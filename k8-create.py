#!/usr/bin/env python

#######################################
# Terraform:            Creates 3x VM's in KVM based on baseline *.qcow2 disk
#                       Baseline image requires deletion of network profile and re-create at boot via cronjob
# Ansible_Prep:         Collects DHCP IP and creates inventory and ansible.cfg 
# Ansible_Baseline:     Installs and performs configurations required prior to K8 initialization
# Ansible_K8_Config:    Performs "init", token generation and worker node join
# Cleanup:              Removes only the files and directories created by this script
#
#######################################
print("\nVersion: 1.0.0\n")

import os
import subprocess
import re           # used for searching IP
import time         # used to wait for obtaining IP
import pathlib      # used for deleting files
import shutil       # used for deleting dir's

HOME_DIR = os.path.expanduser("~/")

# Execute script in order of functions defined here
#--------------------------------------------------
def main_function():
    Terraform()
    Ansible_Prep()
    Ansible_Baseline()
    Ansible_K8_Config()
    Cleanup()

#Script to:
#    
#    Create storageClss
#    Create NFS mount
#    Create Cloudflare tunnel
#    Install apps from ddelisle repo

#---------------------- START ANSIBLE-K8-CONFIG -----------------------

def Ansible_K8_Config():
    print("Writing Ansible K8 init and config playbook")

k8_playbook = open(HOME_DIR + "k8_playbook.yaml", "w")
    k8_playbook.write('''- hosts: master-001 worker-001 worker-002
  become: true
  vars_files:
    - ./variables.yaml
  tasks:

#---------------------------------> K8 CLUSTER INIT AND BASIC CONFIG

  - name: Initialize K8 Cluster
    shell: kubeadm init --apiserver-advertise-address 192.168.1.200 --control-plane-endpoint 192.168.1.200 --pod-network-cidr=10.244.0.0/16
    delegate_to: master-001

  - name: Add export to root profile
    lineinfile:
      dest: /root/.bashrc
      line: export KUBECONFIG=/etc/kubernetes/admin.conf
    delegate_to: master-001

  - name: Source the root profile
    shell: source ~/.bashrc
    delegate_to: master-001

  - name: Install flannel pod network
    shell: kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
    delegate_to: master-001

  - name: Install NFS CSI
    shell: curl -skSL https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/v4.11.0/deploy/install-driver.sh | bash -s v4.11.0 --
    delegate_to: master-001

  - name: Get kubeadm join command
    command: kubeadm token create --print-join-command
    register: join_command
    delegate_to: master-001

  - name: Execute join command
    command: "{{ join_command.stdout }}" 
    delegate_to: "{{ item }}"
    loop: "{{ groups['worker'] }}"

  - name: Pause for 1 minute for worker nodes to join successfully
    ansible.builtin.pause:
      minutes: 1

  - name: Label the node
    command: kubectl label node worker-001 node-role.kubernetes.io/worker=worker
    delegate_to: master-001

  - name: Label the node
    command: kubectl label node worker-002 node-role.kubernetes.io/worker=worker
    delegate_to: master-001
''')
    k8_playbook.close()
    print("Finished writing Ansible K8 init and config playbook")
    
    print("Waiting for VM's to reboot before creating a new inventory file")
    time.sleep(90)

    print("Creating new inventory file")
    # Remove the previous inventory file and re-write using new IP addresses
    p1 = pathlib.Path(HOME_DIR + "inventory.ini")
    p1.unlink(missing_ok=True)

    hosts = ["master-001", "worker-001", "worker-002"]
    ansible_inv = open(HOME_DIR + "inventory.ini", "w")

    # Execute virsh command to obtain dirty IP list
    for host in hosts:
        virsh_cmd = subprocess.run(["virsh", "domifaddr", host, "--source", "agent"], capture_output=True, text=True)

        # Clean up raw input from virsh execution
        if virsh_cmd.returncode == 0:
            virsh_output = virsh_cmd.stdout
            string_split = virsh_output.strip().split('\n')

            for line in string_split:
            # Regular expression to find valid IPv4 addresses and omit loopback
                ip_match = re.search(r'\b(?:(?!127\.0\.0\.1)(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', line)

                # Change group match to string and write to ini file
                if ip_match:
                    ip = ip_match.group()
                    if host == "master-001":
                        ansible_inv.write("[master]\n")
                    if host == "worker-001":
                        ansible_inv.write("[worker]\n")
                    ansible_inv.write(host + " ansible_host=" + ip + "\n")
        else:
            print(f"Command failed with error code {virsh_cmd.returncode}: {virsh_cmd.stderr}")
    ansible_inv.close()
    print("Completed writing new inventory file")

    def run_ansible_playbook(playbook_path, inventory_path):
        print("Applying K8 init and configurations...")
        command = ["ansible-playbook", "--user", "root", "--ask-pass", playbook_path]

        if inventory_path:
            command.extend(["-i", inventory_path])
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            return stdout.decode(), stderr.decode()
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    if __name__ == '__main__':
        playbook_path = HOME_DIR + "k8_playbook.yaml"
        inventory_path = HOME_DIR + "inventory.ini"

        output, error = run_ansible_playbook(playbook_path, inventory_path)

        if output:
            print("Standard Output:")
            print(output)
        if error:
            print("Standard Error:")
            print(error)

#----------------------- END ANSIBLE-K8-CONFIG ------------------------

#----------------------- START ANSIBLE-BASELINE -----------------------

def Ansible_Baseline():
    print("Writing Ansible 'baseline' software install and configuration playbook")
    baseline_playbook = open(HOME_DIR + "baseline_playbook.yaml", "w")
    baseline_playbook.write('''- hosts: master-001 worker-001 worker-002
  become: true
  vars_files:
    - ./variables.yaml
  tasks:

#---------------------------------> ENABLE REPO'S

  - name: Add kubernetes repo
    yum_repository:
      name: kubernetes
      description: Repo for K8-on-KVM
      baseurl: "https://pkgs.k8s.io/core:/stable:/v1.28/rpm/"
      gpgcheck: yes
      gpgkey: https://pkgs.k8s.io/core:/stable:/v1.28/rpm/repodata/repomd.xml.key

  - name: Add CRI-O repo
    yum_repository:
      name: cri-o
      description: Repo for K8-on-KVM
      baseurl: "https://pkgs.k8s.io/addons:/cri-o:/prerelease:/main/rpm/"
      gpgcheck: yes
      gpgkey: https://pkgs.k8s.io/addons:/cri-o:/prerelease:/main/rpm/repodata/repomd.xml.key

#---------------------------------> INSTALL SOFTWARE

  - name: Install K8 Binaries
    ansible.builtin.dnf:
      name: "{{ packages }}"
    vars:
      packages:
        - kubeadm
        - kubectl
        - kubelet
      state: present

  - name: Install CRI-O
    ansible.builtin.dnf:
      name: "{{ packages }}"
    vars:
      packages:
        - cri-o
      state: present

  - name: Install Base Packages for Kubernestes Functionality
    ansible.builtin.dnf:
      name: "{{ packages }}"
    vars:
      packages:
        - conntrack
        - container-selinux
        - ebtables
        - ethtool
        - iptables
        - socat
        - nfs-utils
        - dhcp-client
      state: present

#---------------------------------> MAKE CONFIGURATIONS

  - name: Add k8 nodes to /etc/hosts
    lineinfile:
      dest: /etc/hosts
      line: "{{ item.line }}"
    loop:
      - { line: '192.168.1.200 master-001 master-001' }
      - { line: '192.168.1.201 worker-001 worker-001' }
      - { line: '192.168.1.202 worker-002 worker-002' }

  - name: Disable swap
    shell: |
      swapoff -a
   
  - name: Disable swap from /etc/fstab
    lineinfile:
      path: /etc/fstab
      regexp: 'swap'
      state: absent

  - name: Enable service firewalld
    systemd:
      name: firewalld
      enabled: yes

  - name: Open K8 and NFS - TCP
    firewalld:
      offline: yes
      port: "{{ item }}/tcp"
      permanent: yes
      state: enabled
    loop:
      - 6443
      - 2379
      - 2380
      - 10248
      - 10250
      - 10251
      - 10255
      - 2049

  - name: Open K8 and NFS - UDP
    firewalld:
      offline: yes
      port: "{{ item }}/udp"
      permanent: yes
      state: enabled
    loop:
      - 2049

  - name: Enable mountd Service
    ansible.posix.firewalld:
      service: mountd
      state: enabled
      permanent: true
      immediate: true
      offline: true

  - name: Enable rpc-bind Service
    ansible.posix.firewalld:
      service: rpc-bind
      state: enabled
      permanent: true
      immediate: true
      offline: true

  - name: Load module - br_netfilter
    community.general.modprobe:
      name: br_netfilter
      state: present
      persistent: present

  - name: Load module - overlay
    community.general.modprobe:
      name: overlay
      state: present
      persistent: present

  - name: net.bridge - ip6 tables=1
    sysctl:
      name: net.bridge.bridge-nf-call-ip6tables
      value: 1
      state: present

  - name: net.bridge - iptables=1
    sysctl:
      name: net.bridge.bridge-nf-call-iptables
      value: 1
      state: present

  - name: net ipv4 forwarding
    sysctl:
      name: net.ipv4.ip_forward
      value: 1
      state: present

  - name: Enable and Start kubelet service
    ansible.builtin.service:
      name: kubelet
      state: started
      enabled: true

  - name: Start and enable CRI-O service
    systemd:
      name: crio
      state: started
      enabled: true

  - name: Set hostname
    hostname:
      name: "{{ inventory_hostname }}"

  - name: Add an Ethernet connection with static IP configuration
    community.general.nmcli:
      conn_name: ethernet
      ifname: ens3
      type: ethernet
      ip4: "{{ new_ip }}"
      gw4: 192.168.1.1
      state: present

  - name: Release the DHCP Address and reboot without waiting for reboot to complete
    shell: "dhclient -r && reboot"
    async: 1
    poll: 0    
''')
    baseline_playbook.close()

    # Create variable dir and files necessary for static IP assignment of VM's 
    host_vars_dir = os.mkdir(HOME_DIR + "host_vars")
    host_vars_path = HOME_DIR + "host_vars"

    master001 = open(host_vars_path + "/master-001", "w")
    master001.write("new_ip: 192.168.1.200/24")
    master001.close()

    worker001 = open(host_vars_path + "/worker-001", "w")
    worker001.write("new_ip: 192.168.1.201/24")
    worker001.close()
    
    worker002 = open(host_vars_path + "/worker-002", "w")
    worker002.write("new_ip: 192.168.1.202/24")
    worker002.close()

    print("Completed writing Ansible 'baseline' playbook")

    def run_ansible_playbook(playbook_path, inventory_path):
        print("Applying baseline configurations...")
        command = ["ansible-playbook", "--user", "root", "--ask-pass", playbook_path]

        if inventory_path:
            command.extend(["-i", inventory_path])
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            return stdout.decode(), stderr.decode()
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    if __name__ == '__main__':
        playbook_path = HOME_DIR + "baseline_playbook.yaml"
        inventory_path = HOME_DIR + "inventory.ini"
    
        output, error = run_ansible_playbook(playbook_path, inventory_path)
    
        if output:
            print("Standard Output:")
            print(output)
        if error:
            print("Standard Error:")
            print(error)

#----------------------- START ANSIBLE-BASELINE -----------------------

#----------------------- START ANSIBLE-PREP -----------------------

def Ansible_Prep():
    print(f"Waiting 1 minute for VM's to obtain an IP Addresses")
    time.sleep(60)

    # Execute the virsh command on each host and write to the inventory file
    hosts = ["master-001", "worker-001", "worker-002"]
    ansible_inv = open(HOME_DIR + "inventory.ini", "w")

    # Execute virsh command to obtain dirty IP list
    for host in hosts:
        virsh_cmd = subprocess.run(["virsh", "domifaddr", host, "--source", "agent"], capture_output=True, text=True)
    
        # Clean up raw input from virsh execution
        if virsh_cmd.returncode == 0:
            virsh_output = virsh_cmd.stdout
            string_split = virsh_output.strip().split('\n')

            for line in string_split:
                # Regular expression to find valid IPv4 addresses and omit loopback
                ip_match = re.search(r'\b(?:(?!127\.0\.0\.1)(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', line)
                
                # Change group match to string and write to ini file
                if ip_match:
                    ip = ip_match.group()
                    ansible_inv.write(host + " ansible_host=" + ip + "\n")
        else:
            print(f"Command failed with error code {virsh_cmd.returncode}: {virsh_cmd.stderr}")
    ansible_inv.close()
    print("Wrote IP Addresses to inventory file")

    # Create ansible config file
    ansible_cfg = open(HOME_DIR + "ansible.cfg", "w")
    ansible_cfg.write('''[defaults]
host_key_checking = False
deprecation_warnings = False
interpreter_python = auto_silent
ansible_connection_timeout = 5''')
    ansible_cfg.close()
    print ("Wrote Ansible Configuration file")

#---------------------- END ANSIBLE-PREP -----------------------


#----------------------- START TERRAFORM -----------------------

def Terraform():
# Baseline VM created and disk located under mounted path 
    try:
        with open("/mnt/usb_drive/kvm/disk/ol9-kvm-baseline.qcow2", "r") as f:
            print("Baseline qcow2 file exists... continuing")
            
    except FileNotFoundError:
        print("Basline qcow file NOT found... exiting")
        exit()

# Create terraform main.tf, write the config and and close the stream
    print("Creating main.tf")
    terraform_file = open(HOME_DIR + "main.tf", "w")
    terraform_file.write('''terraform {
  required_providers {
    libvirt = {
      source = "dmacvicar/libvirt"
      version = "0.8.3"
    }
  }
}
provider "libvirt" {
  uri = "qemu:///system"
}
locals {
  host_list = toset([ "master-001", "worker-001", "worker-002"])
}
resource "libvirt_volume" "ol9-kvm-baseline" {
  for_each = local.host_list
  name = "${each.key}.qcow2"
  pool = "disk"
  source = "/mnt/usb_drive/kvm/disk/ol9-kvm-baseline.qcow2"
  format = "qcow2"
}
resource "libvirt_domain" "ol9-kvm-baseline" {
  for_each = local.host_list
  name = each.key
  memory = "8096"
  vcpu = 4
  cpu {
    mode = "host-passthrough"
  }
  disk {
    volume_id = libvirt_volume.ol9-kvm-baseline[each.key].id
  }
  console {
    type = "pty"
    target_type = "serial"
    target_port = "0"
  }
  graphics {
    type = "vnc"
    listen_type = "address"
    listen_address = "0.0.0.0"
    autoport = true
  }
  network_interface {
    bridge = "br0"
  }
}''')
    terraform_file.close()

# Execute terraform "init" and "plan"
    subprocess.run(["terraform", "init"])
    subprocess.run(["terraform", "plan"])

# Obtain input from operator if they want to proceed with "apply"
    name = input("Type YES or NO to apply the configuration: ")
    if name == "NO": 
        print("No was typed... Exiting")
        exit()
    else:
        print("Executing... (will update once completed)")
        subprocess.run(['terraform', 'apply', '-auto-approve'])
        print("Complete. VM's have been deployed\n")
    return

#----------------------- END TERRAFORM -----------------------

#----------------------- START CLEAN UP ----------------------

def Cleanup():

    print("Cleaning up created files")
    p1 = pathlib.Path(HOME_DIR + "main.tf")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "ansible.cfg")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "baseline_playbook.yaml")
    p1.unlink(missing_ok=True)

    p2 = pathlib.Path(HOME_DIR + "inventory.ini")
    p2.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "terraform.tfstate")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "terraform.tfstate.backup")
    p1.unlink(missing_ok=True)

    path = (HOME_DIR + "host_vars")
    shutil.rmtree(path, ignore_errors=True)

    p2 = pathlib.Path(HOME_DIR + "k8_playbook.yaml")
    p2.unlink(missing_ok=True)

    print(f"Files have been cleaned up successfully\n")

#---------------------- FINISH CLEAN UP ----------------------

main_function()

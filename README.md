# k8-on-kvm

Automated K8 on KVM:
====================
This automated process requires the following information prior to execution:

1) You have a type 2 KVM hypervisor setup on Oracle Linux 9

2) A network bridge is configured on the host and LibVirt environment named: br0

3) Your network has static IP Addresses available:
   - 192.168.1.200 - Will be used for master-001
   - 192.168.1.201 - Will be used for worker-001
   - 192.168.1.202 - Will be used for worker-002

5) The following software is installed on the host:
 
 -  Terraform
 
 - Ansible and "ansible-playbook" located at: ~/.local/bin/ansible-playbook
 
 - Ansible Modules:
....community.kubernetes
....ansible.posix
....community.general
 
5) Baseline *.qcow2 disk image is named, located, and has read permissions at location: /mnt/usb_drive/kvm/disk/ol9-kvm-baseline.qcow2

6) Read permissions to the baseline qcow2 file location

7) Quick Emulator URI is set to system in your .bashrc profile: export LIBVIRT_DEFAULT_URI="qemu:///system"

8) Ansible uses password authentication for managed nodes and executes switch: "--user root --ask-pass" when launching: ansible-playbook



Process Taken to Create Script:
===============================

-------------------
CREATE BASELINE VM:
-------------------
sudo virt-install \
    --name=ol9-kvm-baseline \
    --ram=8096 \
    --vcpus=4 \
    --os-variant=ol9.5 \
    --disk path=/mnt/usb_drive/kvm/disk/ol9-kvm-baseline.qcow2,size=30 \
    --cdrom=/mnt/usb_drive/kvm/iso/OracleLinux-R9-U5-x86_64-dvd.iso \
    --network bridge=br0 \
    --console pty,target_type=serial \
    --graphics vnc,listen=0.0.0.0

------------------------------
INSTALL STEPS FOR BASELINE VM:
------------------------------
1) Select options:
 - Server with GUI
 - Root password set
 - Allow root SSH login
 - Confirm 30Gb disk
 - Timezone
 - Start the install
 - Reboot when finished

Boot

2) From Virtual Machine Manager:
 - Create user and login
 - Logout of created user account and login as "root"
 - Delete user created for first login
 - Delete the network interface "profile"

3) From the terminal execute: "crontab -e" and add the following lines:
@reboot /usr/bin/nmcli con add type ethernet
@reboot crontab -r

4) Save and close crontab editor followed by executing "shutdown now"

-----------------------------
EXECUTE "K8-CREATE.PY" SCRIPT
-----------------------------
1) Run the K8-create script and follow the prompts:
./k8-create.py

2) Enter "YES" to apply the terraform plan and create 3x VM's based on your baseline.

3) When prompted, enter the VM's root password for the ansible baseline configuration to be applied

4) When prompted, enter the VM's root password for the ansible k8 init, join and configuration to be applied

5) Script will automatically cleanup files it created and take about 13 minutes to commplete


NOTE: Not all exception handling has been implemented as enhancements are still being made. Having some familiarity with python and functions blocks will be helpful if errors are encountered. That or, reach out to helpdesk...


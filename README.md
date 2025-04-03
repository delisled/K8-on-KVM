# k8-on-kvm

==================================
AUTOMATED K8 on KVM (k8-create.py)
==================================
This automated process requires the following information prior to execution:
1) You have a type 2 KVM hypervisor setup on Oracle Linux 9
2) A network bridge is configured on the host and LibVirt environment named: br0
3) Your network has static IP Addresses available:
   - 192.168.1.200 - Will be used for master-001
   - 192.168.1.201 - Will be used for worker-001
   - 192.168.1.202 - Will be used for worker-002
5) The following software is installed on the host:
 - Terraform
 - Ansible and "ansible-playbook" located at: ~/.local/bin/ansible-playbook
 - Ansible Modules:
....community.kubernetes
....ansible.posix
....community.general
6) Baseline *.qcow2 disk image is named, located, and has read permissions at location: /mnt/usb_drive/kvm/disk/ol9-kvm-baseline.qcow2
7) Read permissions to the baseline qcow2 file location
8) Quick Emulator URI is set to system in your .bashrc profile: export LIBVIRT_DEFAULT_URI="qemu:///system"
9) Ansible uses password authentication for managed nodes and executes switch: "--user root --ask-pass" when launching: ansible-playbook

-------------------------------
Executing "k8-create-py" script
-------------------------------
1) Run the K8-create script from your KVM host and follow the prompts:
./k8-create.py
2) Enter "YES" to apply the terraform plan and create 3x VM's based on your baseline.
3) When prompted, enter the VM's root password for ansible baseline configuration to be applied
4) When prompted, enter the VM's root password for ansible k8 configuration and master node init
5) When prompted, enter the VM's root password for ansible worker node join
6) Script will automatically cleanup files created and will take about 15 minutes to commplete

NOTE: Not all exception handling has been implemented so here's hoping you have some familiarity with python and the function blocks created if errors are encountered


==========================================
AUTOMATED K8 on KVM (k8-kvm-cloudflare.py)
==========================================
This interactive script requires the following information prior to execution:
1) This script is executed on the kubernetes "master" node
2) You have sudo rights on the "master" node
3) The "master" node has a GUI and web browser installed
4) You have a Cloudflare account and have associated your Domain and DNS with Cloudflare
5) You have created a "user token" with permissions and resources as outlined below:
 - Token created from this link (after you login to Cloudflare): https://dash.cloudflare.com/profile/api-tokens
 - Token provides the following cloudflare permissions and resources:
------------
Permissions:
-----------------------------------------
Account   || Cloudflare Tunnel	||Read
-----------------------------------------
Zone      || DNS         			||Edit
-----------------------------------------

-----------------------------------------
Account Resources:
-----------------------------------------
Include   || [emailAddress]
-----------------------------------------

-----------------------------------------
Zone Resource:
-----------------------------------------
Include	|| [your email address]
-----------------------------------------

 - Once complete, select "Summary" and then obtain your token

NOTE: You will need the resulting API TOKEN in order to create a secret in kubernetes. Save it somewhere for copy/paste after executing the script
NOTE: If you have one but misplaced the API TOKEN, delete the old and create a new one with the above settings. Just make sure it's a "User API Token"


---------------------------------------
Executing "k8-kvm-cloudflare.py" script
---------------------------------------
1) On the "Master Node", login to your cloudflare account
2) On the "Master Node", open a terminal and execute: ./k8-kvm-cloudflare.py
3) Enter your Cloudflare User API Token:
4) Enter your Cloudflare Email Address:
5) When prompted, navigate to the browser window and complete authentication by selecting your account and authorizing. Leave the browser open
6) Enter a name for your tunnel:
7) Once complete, navigate to the cloudflare dashboard and modify the SSL/TLS Encryption Mode to FULL and make sure there is a 'Universal' certificate.
 - The SSL/TLS Encryption Mode setting is located at:
   a. Account Home
   b. Select the vertical dots on the far right side of your active domain name and select "Configure SSL/TLS"
 - The 'Universal' certificate setting is located at:
   a. After selecting the SSL/TLS Mode setting as defined above, a different menu will appear on the left side
   b. Select: "Edge Certificates" option and verify if you have a 'Universal' certificate. If not, select: "Order Advanced Certificate" and choose the free option
8) Once complete, in the terminal window; select the ENTER button to continue
9) Provide your Cloudflare Tunnel ID: (this was provided after your entered your "tunnel name" - copy/paste it here)
10) Provide your Cloudflare Domain Name:
11) Wait for the script to complete
12) Check the status of pods in the cloudflare namespace. If they stay online for longer than 70 seconds without restarting, check the status of your tunnel on the cloudflare website by navigating to:
 - Account Home
 - Zero Trust
 - Networks
 - Tunnels

If the pod stayed up for longer than 70 seconds; your tunnel should be "HEALTHY"

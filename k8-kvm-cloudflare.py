#!/usr/bin/env python

#######################################
# This script assumes you have:
# - Cloudflare account and domain/DNS is associated correctly
# - Kubernetes cluster and have admin access
#
# MasterNodePrep:       Installs software and repo's for script to run
# CloudFlareInstall:    Installs cloudflared and authenticates
# Ansible_Config:       Configures K8 for cloudflare use
# Cleanup:              Removes only files and dir's created by this script (except necessary cloudflare token information)
#
#######################################

import os
import subprocess
import re           # used for searching Tunnel ID
import time         # used to wait
import pathlib      # used for deleting files

print("\nVersion: 1.0.1\n----------------------------------------------------------\n")
print("NOTE: If this is a fresh K8 install, the master node should be rebooted one more time\n")
def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timer = '{:02d}'.format(secs)
        print("Starting script in: " + timer, end="\r")
        time.sleep(1)
        t -= 1
countdown(5)
print("----------------------------------------------------------")


HOME_DIR = os.path.expanduser("~/")


# Execute script in order of functions defined here
#--------------------------------------------------
def main_function():
    MasterNodePrep()
    CloudFlareInstall()
    CloudFlareSetup()
    Cleanup()

#------------------------- START CLOUDFLARE SETUP -----------------------

def CloudFlareSetup():
    # Request name of the tunnel to be created
    
    tunnel_name = input("Enter a name for your tunnel (Eg. home-lab, etc): ")
    print("----------------------------------------------------------")
    # Create Cloudflare API Token Secret
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "cloudflared tunnel create " + tunnel_name
        subprocess.run(command, shell=True, check=True)
        print("\nThe tunnel has been created successfully\n\nNavigate to the cloudflare dashboard and modify the SSL/TLS Encryption Mode to FULL and make sure there is a 'Universal' certificate\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

    input("\nHit ENTER once complete...\n")

    print("----------------------------------------------------------")
    print("Obtaining JSON file from " + HOME_DIR + ".cloudflared/")
    path = HOME_DIR + ".cloudflared/"
    cf_json_file = os.listdir(path)

    # Create Cloudflare Tunnel Secret
    print("Creating Cloudflare Tunnel Kubernetes Secret")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl create secret generic tunnel-credentials --from-file=credentials.json=" + HOME_DIR + ".cloudflared/" + cf_json_file[1] + " --namespace=cloudflare"
        subprocess.run(command, shell=True, check=True)
        print("----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")
    
    print("Provide your Cloudflare Tunnel ID")
    tunnel_id = input("NOTE: This was provided earlier: ")
    domain_name = input("Provide your Cloudflare Domain Name: ")

    print("----------------------------------------------------------")
    print("Creating the Cloudflare tunnel manifest")
    manifest_string = f"""cloudflare:
  tunnelName: "{tunnel_name}"
  tunnelId: "{tunnel_id}"  
  secretName: "tunnel-credentials"
  ingress:
    - hostname: "*.{domain_name}"
      service: "https://ingress-nginx-controller.kube-system.svc.cluster.local:443"
      originRequest:
        noTLSVerify: true

resources:
  limits:
    cpu: "100m"
    memory: "128Mi"
  requests:
    cpu: "100m"
    memory: "128Mi"

replicaCount: 1"""
    
    tunnel_manifest = open(HOME_DIR + "tunnel-manifest.yaml", "w")
    tunnel_manifest.write(manifest_string) 
    tunnel_manifest.close()
    print("Finished creating the manifest\n----------------------------------------------------------")

   # Establish Cloudflare Tunnel
    print("Integrating Cloudflare Tunnel with Kubernetes")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm upgrade --install cloudflare cloudflare/cloudflare-tunnel --namespace cloudflare --values tunnel-manifest.yaml --wait"
        subprocess.run(command, shell=True, check=True)
        print("----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

    # Check deployment status
    def k8_deploy_chk():
        print("Checking status of Cloudflare Tunnel / Kubernetes deployment")
        command = ["kubectl", "get", "deploy", "-n", "cloudflare", "cloudflare-cloudflare-tunnel"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Status check of deployment was successful\n----------------------------------------------------------")
            return process.stdout
        else:
            print(f"There was an error checking status of deployment...")
            print(process.stderr + "----------------------------------------------------------")
    tun_result = k8_deploy_chk()
    tun_result = tun_result.strip()
    print(tun_result)
    print("----------------------------------------------------------")

    # Adding external DNS
    try:
        # Command(s) to be executed inside a single subprocess shell
        print("Installing External DNS (used to manage sub-domains in Cloudflare)")
        command = "helm upgrade --install external-dns kubernetes-sigs/external-dns --namespace cloudflare --set sources[0]=ingress --set policy=sync --set provider.name=cloudflare --set env[0].name=CF_API_TOKEN --set env[0].valueFrom.secretKeyRef.name=cloudflare-api-key --set env[0].valueFrom.secretKeyRef.key=apiKey --wait"
        subprocess.run(command, shell=True, check=True)
        print("...Installed External DNS successfully\n----------------------------------------------------------\n")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred installing External DNS: {e}----------------------------------------------------------")

    # Check deployment status
    def k8_dns_chk():
        print("Checking status of External DNS deployment")
        command = ["kubectl", "get", "deploy", "-n", "cloudflare", "external-dns"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Check of External DNS deployment was successful\n----------------------------------------------------------")
            return process.stdout
        else:
            print(f"There was an error checking status of External DNS deployment...")
            print(process.stderr + "----------------------------------------------------------")
    dns_result = k8_deploy_chk()
    dns_result = dns_result.strip()
    print(dns_result)
    print("----------------------------------------------------------")

#-------------------------- END CLOUDFLARE SETUP ------------------------

#----------------------- START CLOUDFLARE INSTALL -----------------------

def CloudFlareInstall():

    # Request user created token in order to create a K8 secret
    user_token = input("Enter your Cloudflare User API Token: ")

    # Request email address for cloudflare account
    user_email = input("Enter your Cloudflare Email Address: ")

    # Create Cloudflare API Token Secret
    print("Creating Cloudflare API Token Secret")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl create secret generic cloudflare-api-key --from-literal=apiKey=" + user_token + " --from-literal=email=" + user_email + " --namespace=cloudflare"
        subprocess.run(command, shell=True, check=True)
        print("...Created Cloudflare API Token Secret successfully\n----------------------------------------------------------\n")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

    print("Installing cloudflared...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "pushd $(mktemp -d) && curl -sSL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && sudo install -m 555 cloudflared /usr/local/bin/cloudflared && rm cloudflared && popd"
        subprocess.run(command, shell=True, check=True)
        print("...installed cloudflared successfully\n----------------------------------------------------------\n")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

    print("\nGoing to launch Cloudflare Tunnel on this 'Master' node. If the browser doesnt automatically open, make sure to open the link provided in the master node's browser. When done, this script will automatically continue.\n----------------------------------------------------------\n") 

    # Login to cloudflare tunnel
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "/usr/local/bin/cloudflared tunnel login"
        subprocess.run(command, shell=True, check=True)
        print("...Logged into the cloudflare web successfully\n----------------------------------------------------------\n")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

    # Install nginx-controller as default ingress
    try:    
        print("Adding Kubernetes Nginx-Ingress as default Ingress")
        command = "helm upgrade -i ingress-nginx ingress-nginx/ingress-nginx --namespace kube-system --set controller.service.type=ClusterIP --set controller.ingressClassResource.default=true --wait"
        subprocess.run(command, shell=True, check=True)
        print("...Created Kubernetes Nginx-Ingress successfully\n----------------------------------------------------------\n")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

#----------------------- END CLOUDFLARE INSTALL -----------------------

#----------------------- START MASTER NODE PREP -----------------------

def MasterNodePrep():

    # Check if software is installed - Install it if not already
    sw_name = ["helm"]
    for pkg in sw_name:
        rc = subprocess.call(['which', pkg])
        if rc == 0:
            print(pkg + " is installed...\n----------------------------------------------------------")
        else:
            print(pkg + " not installed...")

            def install_helm():
                print("...Installing Helm\n----------------------------------------------------------")
                command = ["curl", "-fsSL", "-o", "get_helm.sh", "https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3"]
                process = subprocess.run(command, capture_output=True, text=True)
                if process.returncode == 0:
                    shell_script = HOME_DIR + "get_helm.sh"
                    os.chmod(shell_script, 0o755)
                    subprocess.run(shell_script)
                else:
                    print(f"There was an error trying to install Helm - Try to install manually - Exiting...")
                    print(process.stderr)
                    exit()

            if pkg == "helm":
                install_helm()

    # Add nginx repo 
    def add_nginx_repo(repo_name, repo_url):
        print("Adding Nginx Repo")
        command = ["helm", "repo", "add", repo_name, repo_url]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print(f"Nginx Repo added successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error trying to add Nginx Repo - Try to add manually - Exiting\n----------------------------------------------------------")
            print(process.stderr)
            exit()
    repo_name = "ingress-nginx"
    repo_url = "https://kubernetes.github.io/ingress-nginx"
    add_nginx_repo(repo_name, repo_url)

    # Add k8-sigs repo 
    def add_k8_sigs_repo(repo_name, repo_url):
        print("Adding Kubernetes Sigs (for External-DNS) Repo")
        command = ["helm", "repo", "add", repo_name, repo_url]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print(f"Kubernetes Sigs Repo added successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error trying to add Kubernetes Sigs Repo - Try to add manually - Exiting\n----------------------------------------------------------")
            print(process.stderr)
            exit()
    repo_name = "kubernetes-sigs"
    repo_url = "https://kubernetes-sigs.github.io/external-dns/"
    add_k8_sigs_repo(repo_name, repo_url)

    # Add cloudflare repo
    def add_cloudflare_repo(repo_name, repo_url):
        print("Adding Cloudflare Repo")
        command = ["helm", "repo", "add", repo_name, repo_url]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print(f"Cloudflare Repo added successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error trying to add Cloudflare Repo - Try to add manually - Exiting\n----------------------------------------------------------")
            print(process.stderr)
            exit()
    repo_name = "cloudflare"
    repo_url = "https://cloudflare.github.io/helm-charts"
    add_cloudflare_repo(repo_name, repo_url)

    def helm_update():
        print("Updating Helm")
        command = ["helm", "repo", "update"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Helm updated successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error trying to update Helm - Try to update manually - Exiting...\n----------------------------------------------------------")
            print(process.stderr)
            exit()
    helm_update()

    # Create Cloudflare namespace
    def cf_k8_namespace():
        print("Creating cloudflare namespace")
        command = ["kubectl", "create", "namespace", "cloudflare"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Created cloudflare namespace successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error creating namespace: cloudflare...")
            print(process.stderr + "----------------------------------------------------------")
    cf_k8_namespace()

#-------------------- END MASTER NODE PREP -----------------------

#----------------------- START CLEAN UP --------------------------

def Cleanup():

    print("Cleaning up created files")
    p1 = pathlib.Path(HOME_DIR + "get_helm.sh")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "tunnel-manifest.yaml")
    p1.unlink(missing_ok=True)

    print("\nk8-kvm-cloudflare completed successfully\n")

    print("Check the Cloudflare POD status by executing:\nkubectl get pod -n cloudflare")

#---------------------- FINISH CLEAN UP ----------------------

main_function()

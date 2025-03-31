#!/usr/bin/env python

#######################################
# This script assumes you have:
# - Cloudflare account and domain/DNS is associated correctly
# - Kubernetes cluster and have admin access
#
# MasterNodePrep:       Installs software required for script to run
# CloudFlareInstall:    Installs cloudflared and authenticates
# Ansible_Config:       Configures the system for cloudflare use
# Cleanup:              Removes only files and dir's created by this script (except necessary cloudflare account information summary)
#
#######################################
print("\nVersion: 1.0.0\n----------------------------------------------------------")

import os
import subprocess
import re           # used for searching Tunnel ID
import time         # used to wait for deployment status
import pathlib      # used for deleting files
import shutil       # used for deleting dir's

HOME_DIR = os.path.expanduser("~/")

# Execute script in order of functions defined here
#--------------------------------------------------
def main_function():
#    MasterNodePrep()
#    CloudFlareInstall()
    CloudFlareSetup()
    Cleanup() #- this should include SW that has vulnerabilities on NIST (check it out as this could be production code)

#------------------------- START CLOUDFLARE SETUP -----------------------

def CloudFlareSetup():
    # Request name of the tunnel to be created
    tunnel_name = input("Enter a name for your tunnel (Eg. home-lab, etc): ")
    def cf_tun_name():
        command = ["cloudflared", "tunnel", "create", tunnel_name]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("The tunnel has been created successfully\n\nNavigate to the cloudflare dashboard and modify the SSL/TLS Encryption Mode to FULL and make sure there is a 'Universal' certificate\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error creating the tunnel...")
            print(process.stderr + "----------------------------------------------------------")
    cf_tun_name()

    # Obtain *.json file PATH from /root/.cloudflared/ directory
    print("Obtaining JSON file from " + HOME_DIR + ".cloudflared/ and generating a K8 secret")
    path = HOME_DIR + ".cloudflared/"
    cf_json_file = os.listdir(path)

    def cf_tun_secret():
        command = ["kubectl", "create", "secret", "generic", "tunnel-credentials", "--from-file=credentials.json=" + HOME_DIR + ".cloudflared/" + cf_json_file[0], "--namespace=cloudflare"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Created cloudflare tunnel secret successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error creating the tunnel secret...")
            print(process.stderr + "----------------------------------------------------------")
    cf_tun_secret()

    # Change the json file variable format from list to string - works only if there's 1x file in the /root/.cloudflare/ dir
    print("Obtaining the Tunnel ID")
    json_string_format = ", ".join(cf_json_file)

    # Extract the Tunnel ID which is the alpha-numeric string of .json file
    def extract_text(json_string_format):
        match = re.match(r"^[^.]*", json_string_format)
        if match:
            return match.group(0)
        return None
    tunnel_id = extract_text(json_string_format)
    print("Tunnel ID obtained\n----------------------------------------------------------")

    domain_name = input("Provide your domain name associated with cloudflare: ")

    print("----------------------------------------------------------")
    print("Creating the Cloudflare tunnel manifest")
    manifest_string = f"""cloudflare:
  tunnelName: {tunnel_name}
  tunnelId: {tunnel_id}  
  secretName: tunnel-credentials
  ingress:
    - hostname: "*.{domain_name}"
      service: https://ingress-nginx-controller.kube-system.svc.cluster.local:443
      originRequest:
        noTLSVerify: true

resources:
  limits:
    cpu: "100m"
    memory: "128M"
  requests:
    cpu: "100m"
    memory: "128M"

replicaCount: 1"""
    tunnel_manifest = open(HOME_DIR + "tunnel-manifest.yaml", "w")
    tunnel_manifest.write(manifest_string) 
    tunnel_manifest.close()
    print("Finished creating the manifest\n----------------------------------------------------------")

    # Establish Cloudflare tunnel
    def cf_k8_tunnel():
        print("Executing deployment of Cloudflare Tunnel")
        command = ["helm", "upgrade", "--install", "cloudflare", "cloudflare/cloudflare-tunnel", "--namespace", "cloudflare", "--values", "tunnel-manifest.yaml", "--wait"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Execution of deployment of Cloudflare Tunnel successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error with deployment of Cloudflare Tunnel...")
            print(process.stderr + "----------------------------------------------------------")
    cf_k8_tunnel()

    # Check deployment status
    def k8_deploy_chk():
        print("Checking status of Cloudflare Tunnel deployment")

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

    # Adding External-DNS
    print("Installing External DNS (used to manage sub-domains in Cloudflare)")
    def install_dns():
        command = ["helm", "upgrade", "--install", "external-dns", "kubernetes-sigs/external-dns", "--namespace", "cloudflare", "--set", "sources[0]=ingress", "--set", "policy=sync", "--set", "provider.name=cloudflare", "--set", "env[0].name=CF_API_TOKEN", "--set", "env[0].valueFrom.secretKeyRef.key=apiKey", "--wait"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Installed External DNS successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error installing External DNS...")
            print(process.stderr + "----------------------------------------------------------")
    install_dns()

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

    # Request user created token in order to create a K8 secret
    user_token = input("Enter your Cloudflare User API Token: ")

    # Request email address for cloudflare account
    user_email = input("Enter your Cloudflare Email Address: ")

    def create_cf_secret():
        command = ["kubectl", "create", "secret", "generic", "cloudflare-api-key", "--from-literal=apiKey=" + user_token, "--from-literal=email=" + user_email, "--namespace=cloudflare"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print("Created K8 Secret successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error trying to create secret for CloudFlare...")
            print(process.stderr + "----------------------------------------------------------")
    create_cf_secret()

    print("Installing cloudflared...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "pushd $(mktemp -d) && curl -sSL -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && sudo install -m 555 cloudflared /usr/local/bin/cloudflared && rm cloudflared && popd"
        subprocess.run(command, shell=True, check=True)
        print("...installed cloudflared successfully\n----------------------------------------------------------\n")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}----------------------------------------------------------")

    print("\nGoing to launch Cloudflare Tunnel on this 'Master' node. If the browser doesnt automatically open, make sure to open the link provided in the master node's browser. When done, this script will automatically continue.\n----------------------------------------------------------\n") 

    # Login to cloudflare tunnel and capture URL for tunnel creation
    def run_binary_interactively(binary_path, args=None, env=None):
        if args is None:
            args = [binary_path]
        else:
            args = [binary_path] + args
    
        if env is None:
            env = os.environ
    
        pid = os.spawnvpe(os.P_WAIT, binary_path, args, env)
        
        if pid == -1:
            print(f"Error running {binary_path}")
        else:
            print(f"{binary_path} exited with code {os.waitstatus_to_exitcode(os.wait(pid)[1])}")

    binary_path = "/usr/local/bin/cloudflared"
    arguments = ["tunnel", "login"]
    run_binary_interactively(binary_path, arguments)

#----------------------- END CLOUDFLARE INSTALL -----------------------

#----------------------- START MASTER NODE PREP -----------------------

def MasterNodePrep():

    # Check if software is installed - Install it if not already
    sw_name = ["git", "npm", "helm", "wrangler"]
    for pkg in sw_name:
        rc = subprocess.call(['which', pkg])
        if rc == 0:
            print(pkg + " is installed...\n----------------------------------------------------------")
        else:
            print(pkg + " not installed...")

            def install_git():
                print("...Installing GIT")
                command = ["sudo", "dnf", "install", "git", "-y"]
                process = subprocess.run(command, capture_output=True, text=True)
                if process.returncode == 0:
                    return True
                else:
                    print(f"There was an error trying to install GIT - Try to install manually - Exiting...")
                    print(process.stderr)
                    exit()

            def install_npm():
                print("...Installing NPM\n")
                command = ["sudo", "dnf", "install", "npm", "-y"]
                process = subprocess.run(command, capture_output=True, text=True)
                if process.returncode == 0:
                    return True
                else:
                    print(f"There was an error trying to install NPM - Try to install manually - Exiting...")
                    print(process.stderr)
                    exit()
                    
            def install_wrangler():
                print("...Installing Warngler")
                command = ["sudo", "npm", "install", "-g", "@cloudflare/wrangler"]
                process = subprocess.run(command, capture_output=True, text=True)
                if process.returncode == 0:
                    return True
                else:
                    print(f"There was an error trying to install Wrangler - Try to install manually - Exiting...")
                    print(process.stderr)
                    exit()

            def install_helm():
                print("...Installing Helm")
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

            if pkg == "git":
                install_git()
            if pkg == "npm":
                install_npm()
            if pkg == "warngler":
                install_wrangler()
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

    # Add nginx-controller and K8 service
    def add_nginx_ctrl():
        print("Adding Nginx-Controller and K8 Service")
        command = ["helm", "upgrade", "-i", "ingress-nginx", "ingress-nginx/ingress-nginx", "--namespace", "kube-system", "--set", "controller.service.type=ClusterIP", "--set", "controller.ingressClassResource.default=true", "--wait"]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode == 0:
            print(f"Nginx-Controller added successfully\n----------------------------------------------------------")
            return True
        else:
            print(f"There was an error trying to add Nginx-Controller - Try to add manually - Exiting\n----------------------------------------------------------")
            print(process.stderr)
            exit()
    add_nginx_ctrl()

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

#-------------------- END MASTER NODE PREP -----------------------

#----------------------- START CLEAN UP --------------------------

def Cleanup():

    print("Cleaning up created files")
    p1 = pathlib.Path(HOME_DIR + "get_helm.sh")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "tunnel-manifest.yaml")
    p1.unlink(missing_ok=True)

    print("\n\nk8-kvm-cloudflare completed successfully\n\n")

#---------------------- FINISH CLEAN UP ----------------------

main_function()

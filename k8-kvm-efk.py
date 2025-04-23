#!/usr/bin/env python

#######################################
# Config_Create         Creates the repository and all the installation / values files
# Stack_Install         Installs ES, ES Operator, Kibana, Fluent Operator, Fluentbit
# Cleanup:              Removes only files and dir's created by this script
#
#######################################

import os
import subprocess
import time         # used to wait for obtaining IP
import pathlib      # used for deleting files

print("\nVersion: 1.0.1\n----------------------------------------------------------\n")
print("REMINDERS\n - This will be installed into the 'logging' namespace\n - There will various delays between package installations\n")
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
    Config_Create()
    Stack_Install()
    Cert_Install()
    Cleanup()

#----------------------- START CERT INSTALL -------------------------

def Cert_Install():
# Install cert manager
    print("Installing Cert-Manager...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.0/cert-manager.yaml"
        subprocess.run(command, shell=True, check=True)
        print("...installed Cert-Manager successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

# Create secret for cert manager
    print("Creating Secret for Cert-Manager...\n\n")

    apiKey = input("Provide your Cloudflare API key/token: ")
    apiEmail = input("Provide your Cloudflare Email Address: ")

    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl create secret generic cloudflare-api-key --from-literal=apiKey=" + apiKey + " --from-literal=email=" + apiEmail + " --namespace=cert-manager"
        subprocess.run(command, shell=True, check=True)
        print("...Created Secret for Cert-Manager successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

    def countdown(minutes, seconds):
        total_seconds = minutes * 60 + seconds
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            print(timer, end="\r")
            time.sleep(1)
            total_seconds -= 1
    minutes = int("0")
    seconds = int("15")
    countdown(minutes, seconds)

# Create clusterIssuer
    print("Applying ClusterIssuer manifest...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl apply -f clusterIssuer-manifest.yaml"
        subprocess.run(command, shell=True, check=True)
        print("...applied ClusterIssuer manifest successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

# Apply kibana ingress
    print("Applying Kibana Ingress...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl apply -f kibana-ingress.yaml"
        subprocess.run(command, shell=True, check=True)
        print("...applied Kibana successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

#------------------------- END CERT INSTALL ------------------------

#----------------------- START STACK INSTALL -----------------------

def Stack_Install():

# Install Elastic Operator
    print("Installing Elasticsearch Operator...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm install elastic-operator elastic/eck-operator -n logging --create-namespace"
        subprocess.run(command, shell=True, check=True)
        print("...installed Elasticsearch Operator successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

    def countdown(minutes, seconds):
        total_seconds = minutes * 60 + seconds
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            print(timer, end="\r")
            time.sleep(1)
            total_seconds -= 1
    minutes = int("0")
    seconds = int("15")
    countdown(minutes, seconds)

# Install Elasticseach
    print("Installing Elasticsearch...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl apply -f es-storage-deploy.yaml"
        subprocess.run(command, shell=True, check=True)
        print("...installed Elasticsearch successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

    def countdown(minutes, seconds):
        total_seconds = minutes * 60 + seconds
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            print(timer, end="\r")
            time.sleep(1)
            total_seconds -= 1
    minutes = int("2")
    seconds = int("30")
    countdown(minutes, seconds)

# Install Kibana
    print("Installing Kibana...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "kubectl apply -f kibana-deploy.yaml"
        subprocess.run(command, shell=True, check=True)
        print("...installed Kibana successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

    def countdown(minutes, seconds):
        total_seconds = minutes * 60 + seconds
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            print(timer, end="\r")
            time.sleep(1)
            total_seconds -= 1
    minutes = int("3")
    seconds = int("0")
    countdown(minutes, seconds)

# Install Fluentbit Operator
    print("Installing Fluent Operator using CRI: CRIO...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm upgrade --install fluent-operator fluent/fluent-operator --namespace logging --set containerRuntime='crio'"
        subprocess.run(command, shell=True, check=True)
        print("...installed Fluent Operator successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

# Create values.yaml file - no need to wait since ES should be up
    print("Creating values.yaml file for Fluentbit installation...")
    def kubectl_secret(command):
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            print(f"An error occurred: {stderr.decode()}")
        return stdout.decode()

    command = "kubectl get secret quickstart-es-elastic-user -n logging -o go-template='{{.data.elastic | base64decode}}'"
    password = kubectl_secret(command)

# --------------------------------
# IMPORTANT FOR THIS VALUES STRING
# --------------------------------
# 1) Unwanted line values (ONLY UNCOMMENTED) will be applied with double curly brackets {{ }} making them literals in this created values.yaml file
#
# 2) Commented out lines have where this occurs have been deleted
#
# 3) Single curly brackets are references to variables within this script
#
# 4) Double check original values.yaml file by cloning repo with git: https://github.com/fluent/helm-charts/ to utilize the commented out lines
# --------------------------------

    values_string = f"""
# Default values for fluent-bit.

# kind -- DaemonSet or Deployment
kind: DaemonSet

# replicaCount -- Only applicable if kind=Deployment
replicaCount: 1

image:
  repository: cr.fluentbit.io/fluent/fluent-bit
  # Set to "-" to not use the default value
  tag:
  digest:
  pullPolicy: IfNotPresent

testFramework:
  enabled: true
  namespace:
  image:
    repository: busybox
    pullPolicy: Always
    tag: latest
    digest:

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: false
  annotations: {{}}
  name:

rbac:
  create: true
  nodeAccess: false
  eventsAccess: false

# Configure podsecuritypolicy
# Ref: https://kubernetes.io/docs/concepts/policy/pod-security-policy/
# from Kubernetes 1.25, PSP is deprecated
# See: https://kubernetes.io/blog/2022/08/23/kubernetes-v1-25-release/#pod-security-changes
# We automatically disable PSP if Kubernetes version is 1.25 or higher
podSecurityPolicy:
  create: false
  annotations: {{}}
  runAsUser:
    rule: RunAsAny
  seLinux:
    # This policy assumes the nodes are using AppArmor rather than SELinux.
    rule: RunAsAny

# OpenShift-specific configuration
openShift:
  enabled: false
  securityContextConstraints:
    # Create SCC for Fluent-bit and allow use it
    create: true
    name: ""
    annotations: {{}}
    runAsUser:
      type: RunAsAny
    seLinuxContext:
      type: MustRunAs
    # Use existing SCC in cluster, rather then create new one
    existingName: ""

podSecurityContext: {{}}
#   fsGroup: 2000

hostNetwork: true
dnsPolicy: ClusterFirstWithHostNet

dnsConfig: {{}}
#   nameservers:
#     - 1.2.3.4
#   searches:
#     - ns1.svc.cluster-domain.example
#     - my.dns.search.suffix
#   options:
#     - name: ndots
#       value: "2"
#     - name: edns0

hostAliases: []
#   - ip: "1.2.3.4"
#     hostnames:
#     - "foo.local"
#     - "bar.local"

securityContext: {{}}
#   capabilities:
#     drop:
#     - ALL
#   readOnlyRootFilesystem: true
#   runAsNonRoot: true
#   runAsUser: 1000

service:
  type: ClusterIP
  port: 2020
  internalTrafficPolicy:
  loadBalancerClass:
  loadBalancerSourceRanges: []
  loadBalancerIP:
  labels: {{}}
  # nodePort: 30020
  # clusterIP: 172.16.10.1
  annotations: {{}}
  #   prometheus.io/path: "/api/v1/metrics/prometheus"
  #   prometheus.io/port: "2020"
  #   prometheus.io/scrape: "true"
  externalIPs: []
  # externalIPs:
  #  - 2.2.2.2

serviceMonitor:
  enabled: false
  #   namespace: monitoring
  #   interval: 10s
  #   scrapeTimeout: 10s
  #   selector:
  #    prometheus: my-prometheus
  #  ## metric relabel configs to apply to samples before ingestion.
  #  ##
  #  metricRelabelings:
  #    - sourceLabels: [__meta_kubernetes_service_label_cluster]
  #      targetLabel: cluster
  #      regex: (.*)
  #      action: replace
  #  ## relabel configs to apply to samples after ingestion.
  #  ##
  #  relabelings:
  #    - sourceLabels: [__meta_kubernetes_pod_node_name]
  #      separator: ;
  #      regex: ^(.*)$
  #      targetLabel: nodename
  #      replacement: $1
  #      action: replace
  #  scheme: ""
  #  tlsConfig: {{}}

  ## Bear in mind if you want to collect metrics from a different port
  ## you will need to configure the new ports on the extraPorts property.
  additionalEndpoints: []
  # - port: metrics
  #   path: /metrics
  #   interval: 10s
  #   scrapeTimeout: 10s
  #   scheme: ""
  #   # metric relabel configs to apply to samples before ingestion.
  #   #
  #   metricRelabelings:
  #     - sourceLabels: [__meta_kubernetes_service_label_cluster]
  #       targetLabel: cluster
  #       regex: (.*)
  #       action: replace
  #   # relabel configs to apply to samples after ingestion.
  #   #
  #   relabelings:
  #     - sourceLabels: [__meta_kubernetes_pod_node_name]
  #       separator: ;
  #       regex: ^(.*)$
  #       targetLabel: nodename
  #       replacement: $1
  #       action: replace

prometheusRule:
  enabled: false
#   namespace: ""
#   rules:
#   - alert: NoOutputBytesProcessed
#     expr: rate(fluentbit_output_proc_bytes_total[5m]) == 0
#     annotations:
#       message: |
#         bytes for at least 15 minutes.
#       summary: No Output Bytes Processed
#     for: 15m
#     labels:
#       severity: critical

dashboards:
  enabled: false
  labelKey: grafana_dashboard
  labelValue: 1
  annotations: {{}}
  namespace: ""
  deterministicUid: false

lifecycle: {{}}
#   preStop:
#     exec:
#       command: ["/bin/sh", "-c", "sleep 20"]

livenessProbe:
  httpGet:
    path: /
    port: http

readinessProbe:
  httpGet:
    path: /api/v1/health
    port: http

resources: {{}}
#   limits:
#     cpu: 100m
#     memory: 128Mi
#   requests:
#     cpu: 100m
#     memory: 128Mi

## only available if kind is Deployment
ingress:
  enabled: false
  ingressClassName: ""
  annotations: {{}}
  #  kubernetes.io/ingress.class: nginx
  #  kubernetes.io/tls-acme: "true"
  hosts: []
  # - host: fluent-bit.example.tld
  extraHosts: []
  # - host: fluent-bit-extra.example.tld
  ## specify extraPort number
  #   port: 5170
  tls: []
  #  - secretName: fluent-bit-example-tld
  #    hosts:
  #      - fluent-bit.example.tld

## only available if kind is Deployment
autoscaling:
  vpa:
    enabled: false

    annotations: {{}}

    # List of resources that the vertical pod autoscaler can control. Defaults to cpu and memory
    controlledResources: []

    # Define the max allowed resources for the pod
    maxAllowed: {{}}
    # cpu: 200m
    # memory: 100Mi
    # Define the min allowed resources for the pod
    minAllowed: {{}}
    # cpu: 200m
    # memory: 100Mi

    updatePolicy:
      # Specifies whether recommended updates are applied when a Pod is started and whether recommended updates
      # are applied during the life of a Pod. Possible values are "Off", "Initial", "Recreate", and "Auto".
      updateMode: Auto

  enabled: false
  minReplicas: 1
  maxReplicas: 3
  targetCPUUtilizationPercentage: 75
  #  targetMemoryUtilizationPercentage: 75
  ## see https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/#autoscaling-on-multiple-metrics-and-custom-metrics
  customRules: []
  #     - type: Pods
  #       pods:
  #         metric:
  #           name: packets-per-second
  #         target:
  #           type: AverageValue
  #           averageValue: 1k
  ## see https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#support-for-configurable-scaling-behavior
  behavior: {{}}
#      scaleDown:
#        policies:
#          - type: Pods
#            value: 4
#            periodSeconds: 60
#          - type: Percent
#            value: 10
#            periodSeconds: 60

## only available if kind is Deployment
podDisruptionBudget:
  enabled: false
  annotations: {{}}
  maxUnavailable: "30%"

nodeSelector: {{}}

tolerations:
- key: "node-role.kubernetes.io/control-plane"
  effect: "NoSchedule"

affinity: {{}}

labels: {{}}

annotations: {{}}

podAnnotations: {{}}

podLabels: {{}}

## How long (in seconds) a pods needs to be stable before progressing the deployment
##
minReadySeconds:

## How long (in seconds) a pod may take to exit (useful with lifecycle hooks to ensure lb deregistration is done)
##
terminationGracePeriodSeconds:

priorityClassName: ""

env: []
#  - name: FOO
#    value: "bar"

# The envWithTpl array below has the same usage as "env", but is using the tpl function to support templatable string.
# This can be useful when you want to pass dynamic values to the Chart using the helm argument "--set <variable>=<value>"
# https://helm.sh/docs/howto/charts_tips_and_tricks/#using-the-tpl-function
envWithTpl: []
#  - name: FOO_2
#
# foo2: bar2

envFrom: []

# This supports either a structured array or a templatable string
extraContainers: []

# Array mode
# extraContainers:
#   - name: do-something
#     image: busybox
#     command: ['do', 'something']

# String mode
# extraContainers: |-
#   - name: do-something
#     command: ['kubectl', 'version']

flush: 1

metricsPort: 2020

extraPorts: []
#   - port: 5170
#     containerPort: 5170
#     protocol: TCP
#     name: tcp
#     nodePort: 30517

extraVolumes: []

extraVolumeMounts: []

updateStrategy: {{}}
#   type: RollingUpdate
#   rollingUpdate:
#     maxUnavailable: 1

# Make use of a pre-defined configmap instead of the one templated here
existingConfigMap: ""

networkPolicy:
  enabled: false
#   ingress:
#     from: []

# See Lua script configuration example in README.md
luaScripts: {{}}

## https://docs.fluentbit.io/manual/administration/configuring-fluent-bit/classic-mode/configuration-file

config:

  ## https://docs.fluentbit.io/manual/pipeline/parsers
  customParsers: |
    [PARSER]
      Name docker_no_time
      Format json
      Time_Keep Off
      Time_Key time
      Time_Format %Y-%m-%dT%H:%M:%S.%L

  extraFiles:

    fluent-bit.yaml: |

      service:
        flush: 5
        log_level: info
        Daemon: off
        parsers_file: /fluent-bit/etc/parsers.conf
        parsers_file: /fluent-bit/etc/conf/custom_parsers.conf
        HTTP_Server: On
        HTTP_Listen: 0.0.0.0
        HTTP_Port: 2020
        Health_Check: On

      includes:
        - kube-logs.yaml
      
    kube-logs.yaml: |
      pipeline:
        inputs:
          - name: tail
            tag: kube.*
            path: /var/log/containers/*.log
            multiline.parser:
              - docker
              - cri
            Mem_Buf_Limit: 5MB
            Skip_Long_Lines: On
        inputs:
          - name: systemd
            Tag: host.*
            Systemd_Filter: _SYSTEMD_UNIT=kubelet.service
            Read_From_Tail: On

        filters:
          - name: kubernetes
            match: kube.*
            merge_log: on
            keep_log: off
            k8s-logging.parser: on
            K8S-Logging.Exclude: On

        outputs:
          - name: es
            Match: kube.* 
            Host: quickstart-es-http.logging.svc.cluster.local
            tls: On
            tls.verify: Off
            tls.debug: 3
            tls.ca_file: /fluent-bit/tls/tls.crt
            tls.crt_file: /fluent-bit/tls/tls.crt
            HTTP_User: elastic
            HTTP_Passwd: "{password}"
            Logstash_Format: Off
            Suppress_Type_Name: On
            Retry_Limit: False
            index: k8_index

        outputs:
          - name: es
            Match: host.*
            Host: quickstart-es-http.logging.svc.cluster.local
            tls: On
            tls.verify: Off
            tls.debug: 3
            tls.ca_file: /fluent-bit/tls/tls.crt
            tls.crt_file: /fluent-bit/tls/tls.crt
            HTTP_User: elastic
            HTTP_Passwd: "{password}"
            Logstash_Format: Off
            Suppress_Type_Name: On
            Retry_Limit: False
            index: host_index

#     upstream.conf: |
#       [UPSTREAM]
#           upstream1
#
#       [NODE]
#           name       node-1
#           host       127.0.0.1
#           port       43000
#     example.conf: |
#       [OUTPUT]
#           Name example
#           Match foo.*
#           Host bar

# The config volume is mounted by default, either to the existingConfigMap value, or the default of "fluent-bit.fullname"
volumeMounts:
  - name: config
    mountPath: /fluent-bit/etc/conf

daemonSetVolumes:
  - name: varlog
    hostPath:
      path: /var/log
  - name: varlibdockercontainers
    hostPath:
      path: /var/lib/docker/containers
  - name: etcmachineid
    hostPath:
      path: /etc/machine-id
      type: File
  - name: tls-certs
    secret:
      secretName: quickstart-es-http-certs-public

daemonSetVolumeMounts:
  - name: varlog
    mountPath: /var/log
  - name: varlibdockercontainers
    mountPath: /var/lib/docker/containers
    readOnly: true
  - name: etcmachineid
    mountPath: /etc/machine-id
    readOnly: true
  - name: tls-certs
    mountPath: /fluent-bit/tls
    readOnly: true

command:
  - /fluent-bit/bin/fluent-bit

args:
  - --workdir=/fluent-bit/etc/
  - --config=/fluent-bit/etc/conf/fluent-bit.yaml

# This supports either a structured array or a templatable string
initContainers: []

# Array mode
# initContainers:
#   - name: do-something
#     image: bitnami/kubectl:1.22
#     command: ['kubectl', 'version']

# String mode
# initContainers: |-
#   - name: do-something
#     image: bitnami/kubectl:{{ .Capabilities.KubeVersion.Major }}.{{ .Capabilities.KubeVersion.Minor }}
#     command: ['kubectl', 'version']

logLevel: info

hotReload:
  enabled: false
  image:
    repository: ghcr.io/jimmidyson/configmap-reload
    tag: v0.14.0
    digest:
    pullPolicy: IfNotPresent
  resources: {{}}
  extraWatchVolumes: []"""

    values_config = open(HOME_DIR + "values.yaml", "w")
    values_config.write(values_string)
    values_config.close()
    print("Finished creating the values.yaml file\n----------------------------------------------------------")

# Install Fluentbit with values.yaml file
    print("Installing Fluentbit...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm upgrade --install fluent-bit fluent/fluent-bit --values values.yaml --namespace logging"
        subprocess.run(command, shell=True, check=True)
        print("...installed Fluentbit successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

    def countdown(minutes, seconds):
        total_seconds = minutes * 60 + seconds
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = '{:02d}:{:02d}'.format(mins, secs)
            print(timer, end="\r")
            time.sleep(1)
            total_seconds -= 1
    minutes = int("0")
    seconds = int("20")
    countdown(minutes, seconds)

#----------------------- END STACK INSTALL ------------------------

#----------------------- START CONFIGURATION CREATE -----------------------

def Config_Create():

# Add Repo
    print("Adding Fluent/Bit Repo...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm repo add fluent https://fluent.github.io/helm-charts"
        subprocess.run(command, shell=True, check=True)
        print("...installed Fluent/Bit Repo successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

# Add Repo
    print("Adding Elasticsearch Repo...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm repo add elastic https://helm.elastic.co"
        subprocess.run(command, shell=True, check=True)
        print("...installed Elasticsearch Repo successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

# Update Repo
    print("Updating Repo's...")
    try:
        # Command(s) to be executed inside a single subprocess shell
        command = "helm repo update"
        subprocess.run(command, shell=True, check=True)
        print("...updated Repo's successfully\n----------------------------------------------------------")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}\n----------------------------------------------------------")

# Add ES install manifest
    print("Creating Elasticsearch manifest with storage configuation...")

    es_manifest = open(HOME_DIR + "es-storage-deploy.yaml", "w")
    es_manifest.write("""apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: quickstart
  namespace: logging
spec:
  version: 8.17.4
  nodeSets:
  - name: default
    count: 1
    config:
      node.store.allow_mmap: false
    volumeClaimTemplates:
    - metadata:
        name: elasticsearch-data
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 20Gi
        storageClassName: nfs-csi""")
    es_manifest.close()
    print("Elasticsearch manifest completed successfully\n----------------------------------------------------------")

# Add Kibana install manifest
    print("Creating Kibana manifest...")
    kb_install_manifest = open(HOME_DIR + "kibana-deploy.yaml", "w")
    kb_install_manifest.write("""apiVersion: kibana.k8s.elastic.co/v1
kind: Kibana
metadata:
  name: quickstart
  namespace: logging
spec:
  version: 8.17.4
  count: 1
  elasticsearchRef:
    name: quickstart
  http:
    service:
      spec:
        type: ClusterIP""")
    kb_install_manifest.close()
    print("Kibana manifest completed successfully\n----------------------------------------------------------")

# Create manifest for clusterIssuer
    print("Creating ClusterIssuer manifest for letsEncrypt...")
    ci_manifest = open(HOME_DIR + "clusterIssuer-manifest.yaml", "w")
    ci_manifest.write("""apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: cloudflare-letsencrypt
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    privateKeySecretRef:
      name: cloudflare-acme
    solvers:
      - dns01:
          cloudflare:
            apiTokenSecretRef:
              name: cloudflare-api-key
              key: apiKey""")
    ci_manifest.close()
    print("Created ClusterIssuer manifest for letsEncrypt successfully\n----------------------------------------------------------")

# Create ingress for kibana http ClusterIP
    print("Creating Ingress manifest for Kibana...")
    kb_ingress_manifest = open(HOME_DIR + "kibana-ingress.yaml", "w")
    kb_ingress_manifest.write("""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kibana-ingress
  namespace: logging
  annotations:
    nginx.ingress.kubernetes.io/backend-protocol: HTTPS
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    cert-manager.io/cluster-issuer: cloudflare-letsencrypt
    kubernetes.io/tls-acme: "true"
    external-dns.alpha.kubernetes.io/hostname: "kibana.cd3.online"
    external-dns.alpha.kubernetes.io/target: "05471dd3-52f9-40dc-a432-e02858f7a5e1.cfargotunnel.com"
    external-dns.alpha.kubernetes.io/cloudflare-proxied: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - kibana.cd3.online
    secretName: kibana-letsencrypt
  rules:
  - host: kibana.cd3.online
    http:
      paths:
      - backend:
          service:
            name: quickstart-kb-http
            port:
              number: 5601
        path: /
        pathType: Prefix""")
    kb_ingress_manifest.close()
    print("Created Ingress manifest for Kibana successfully\n----------------------------------------------------------")

#---------------------- END CONFIGURATION CREATE -----------------------

#----------------------- START CLEAN UP ----------------------

def Cleanup():

    print("Cleaning up created files")
    p1 = pathlib.Path(HOME_DIR + "es-storage-deploy.yaml")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "kibana-deploy.yaml")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "values.yaml")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "clusterIssuer-manifest.yaml")
    p1.unlink(missing_ok=True)

    p1 = pathlib.Path(HOME_DIR + "kibana-ingress.yaml")
    p1.unlink(missing_ok=True)

    print(f"Files have been cleaned up successfully\n")

#---------------------- FINISH CLEAN UP ----------------------

main_function()

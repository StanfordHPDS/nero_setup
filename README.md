
# Setting up a new Nero instance

<!-- badges: start -->
<!-- badges: end -->

This repository contains instructions for setting up a new Nero instance. First, you'll create a new instance with the `gcloud` command. Then, you'll run a script to install and set up tools that we commonly use.

For example, to create `my-instance` on the Nero project `som-nero-phi-sherrir-afc`, I would run:

```bash
INSTANCE_NAME="${INSTANCE_NAME:-my-instance}"
PROJECT_ID="${PROJECT_ID:-som-nero-phi-sherrir-afc}"
ZONE="${ZONE:-us-west1-c}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-medium}"
DISK_SIZE="${DISK_SIZE:-10}"  # in GB
  
# Recommended as the setup script assumes this OS
IMAGE_NAME="${IMAGE_NAME:-ubuntu-2404-noble-amd64-v20241004}"
IMAGE_PROJECT="${IMAGE_PROJECT:-ubuntu-os-cloud}"

# Create instance with above specs
gcloud compute instances create "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --machine-type="$MACHINE_TYPE" \
  --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=nero-subnet \
  --maintenance-policy=MIGRATE \
  --provisioning-model=STANDARD \
  --service-account=311816845192-compute@developer.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append \
  --tags=ssh \
  --create-disk=auto-delete=yes,boot=yes,device-name="$INSTANCE_NAME",disk-resource-policy="projects/$PROJECT_ID/regions/$(echo $ZONE | cut -d'-' -f1,2)/resourcePolicies/nero-snap-shedule",image="$IMAGE_NAME",image-project="$IMAGE_PROJECT",mode=rw,size="$DISK_SIZE",type=pd-balanced \
  --no-shielded-secure-boot \
  --shielded-vtpm \
  --shielded-integrity-monitoring \
  --labels=goog-ec-src=vm_add-gcloud \
  --reservation-affinity=any
```

Then connect to the server via ssh with:

```bash
gcloud compute ssh --zone "$ZONE" "$INSTANCE_NAME" --project "$PROJECT_ID"
```

When you've successfully ssh'd into the server, run the installation script:

```bash
curl -fsSL https://raw.githubusercontent.com/StanfordHPDS/gcp_setup_script/main/setup.sh \
  -o /tmp/setup.sh && bash /tmp/setup.sh
```

After the script as completed, logout with the `logout` command and log back in with the ports for VS Code and RStudio open. This is also intended to finish updating the paths for all the new software.

```bash
gcloud compute ssh --zone "$ZONE" "$INSTANCE_NAME" --project "$PROJECT_ID" \
  -- -L 8787:localhost:8787 -L 8080:localhost:8080
```

## Using the instance

Each instance has the most recent versions of Python and R available for Ubuntu 24. Both `pip` and `install.packages()` use [Posit Public Package Manager](https://posit.co/products/cloud/public-package-manager/) to install binaries for packages. Additionally, the instance has Quarto, conda, uv, duckdb, gh, tinytex, and Rust installed, as well as a number of common system libraries used in data science packages.

If you think another tool should be included in the default setup, please file an issue or pull request.

### Git and GitHub

Authorize your GitHub credentials with

```bash
gh auth login
```

And tell git who you are

```bash
git config --global user.name "Jane Doe"
git config --global user.email "jane@example.com"
```

### VS Code (<http://localhost:8080/>)

VS Code should now be running. If you open <http://localhost:8080/>, you'll get a start up message that tells you where the credential file is. You can see the password with

```bash
cat /path/to/the/file/code-server/config.yaml
```

Make sure to replace the path with the path in the startup message.

### RStudio Server (<http://localhost:8787/>)

RStudio Server should now be running. You'll need to add a user for yourself. Run

```
sudo adduser your_username
```

and follow the prompts. Then, visit <http://localhost:8787/> and enter the credentials you just created.

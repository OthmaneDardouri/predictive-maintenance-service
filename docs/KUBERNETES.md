# Kubernetes (local, with kind)

## Objects in `k8s/`

| File | Object | Purpose |
|---|---|---|
| `namespace.yaml` | Namespace `pm-service` | groups everything, easy to delete in one go |
| `configmap.yaml` | ConfigMap `api-config` | non-sensitive config (`APP_ENV`, `LOG_LEVEL`, `MODEL_PATH`) as env vars |
| `examples/secret.example.yaml` | Secret (example only) | shape of the secret; the real one is created with `kubectl create secret` |
| `api.yaml` | Deployment + Service `api` | 2 replicas, probes, requests/limits, non-root; ClusterIP service on 8000 |
| `frontend.yaml` | Deployment + Service `frontend` | nginx proxying `/api` to the `api` Service, adding the key from the Secret |
| `hpa.yaml` | HorizontalPodAutoscaler | 2-5 api replicas at 70% CPU of the request |

Probes on the api:
- **startupProbe** `/health`: up to 60 s to start before the other probes run.
- **livenessProbe** `/health`: if the process hangs, Kubernetes restarts the container.
- **readinessProbe** `/ready`: the pod gets traffic only when the model is loaded.

## Step by step

```powershell
# 1. Cluster
kind create cluster --name pm-service

# 2. Images: kind runs in its own container and cannot see local Docker images,
#    so they must be built with a precise tag and loaded into the cluster.
docker build -t pm-service-api:0.1.0 .
docker build -t pm-service-frontend:0.1.0 frontend
kind load docker-image pm-service-api:0.1.0 pm-service-frontend:0.1.0 --name pm-service

# 3. Namespace, then the secret from an environment variable (never from a file in git)
kubectl apply -f k8s/namespace.yaml
$env:API_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
kubectl create secret generic api-secret -n pm-service --from-literal=API_KEY="$env:API_KEY"

# 4. Everything else (check first, then apply)
kubectl apply --dry-run=server -f k8s/
kubectl apply -f k8s/
kubectl get pods -n pm-service -w

# 5. Open the frontend at http://localhost:8080
kubectl port-forward -n pm-service svc/frontend 8080:8080
```

## Operations

```powershell
# Self-healing: the Deployment recreates a deleted pod
kubectl delete pod <api-pod> -n pm-service

# Scale (the HPA will override this if metrics-server is installed)
kubectl scale deployment/api -n pm-service --replicas=3

# Change config: edit the ConfigMap, then restart the pods (env vars are read at start)
kubectl edit configmap api-config -n pm-service
kubectl rollout restart deployment/api -n pm-service

# Rollout and rollback
kubectl set image deployment/api api=pm-service-api:0.2.0 -n pm-service
kubectl rollout status deployment/api -n pm-service
kubectl rollout undo deployment/api -n pm-service

# Clean up everything
kind delete cluster --name pm-service
```

A rollout with a wrong image (tested with `pm-service-api:does-not-exist`) leaves the new
pod in `ImagePullBackOff`, while the old pods keep serving: the rolling update never
removes ready pods before new ones are ready. `rollout undo` brings back the previous
ReplicaSet.

## Debugging a pod that does not start

```powershell
kubectl get pods -n pm-service                  # STATUS: ImagePullBackOff, CrashLoopBackOff, Pending...
kubectl describe pod <pod> -n pm-service        # Events at the bottom: pull errors, failed probes, OOMKilled
kubectl logs <pod> -n pm-service                # app logs (JSON); add --previous after a crash
kubectl get events -n pm-service --sort-by=.lastTimestamp
```

| Status | Usual cause |
|---|---|
| `ImagePullBackOff` / `ErrImagePull` | image not loaded into kind, or wrong tag |
| `CrashLoopBackOff` | app exits at start: check `logs --previous` (e.g. missing `API_KEY`) |
| `Running` but `0/1` Ready | readiness fails: model not loaded, see logs |
| `Pending` | requests larger than the node's free CPU/memory |
| `OOMKilled` (in describe) | memory limit too low |

## HPA and metrics-server

The HPA reads CPU usage from the Metrics API, served by metrics-server, which kind does
not install. Without it, `kubectl get hpa` shows `cpu: <unknown>/70%` and nothing scales.
To install it on kind (it needs `--kubelet-insecure-tls` because kind's kubelet
certificates are self-signed):

```powershell
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type=json -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

Utilization is relative to the CPU **request** (100m): 70% means 70m on average.

## Ingress

Not included. On kind it needs a cluster created with extra port mappings and an
ingress controller (e.g. ingress-nginx) installed. `port-forward` is enough locally;
in the cloud a LoadBalancer Service or an Ingress with a managed controller would expose
the frontend.

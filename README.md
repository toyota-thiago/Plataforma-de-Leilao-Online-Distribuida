# Plataforma-de-Leilao-Online-Distribuida
## Subindo a aplicação Flask
```bash
docker login
docker build -t <USUARIO>/plataforma-de-leilao-online-distribuida:latest .
docker push <USUARIO>/plataforma-de-leilao-online-distribuida:latest
```

## Criando cluster kubernetes com o kind
```bash
cd ..
kind create cluster --name leilao --config kind-config.yaml
```

## Subir Redis e Flask no Kubernetes
```bash
kubectl apply -f k8s/
```

## Rodando a aplicação (no navegador)
```bash
localhost:30080
```
## Realizando testes unitários automatizados 
```bash
cd app
pip install -r requirements.txt
pytest
```
## Realizando testes de carga
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json -p "[{\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/args/-\",\"value\":\"--kubelet-insecure-tls\"},{\"op\":\"add\",\"path\":\"/spec/template/spec/containers/0/args/-\",\"value\":\"--kubelet-preferred-address-types=InternalIP\"}]"
kubectl top nodes
kubectl get hpa

kubectl get pods -w
```
### Em outro terminal, para gerar o tráfego
```bash
kubectl run -it --rm load-generator --image=busybox -- sh
while true; do wget -q -O- http://flask-service:5000/api/auctions; done
```

## IA agêntico
```bash
cd agenteIA
docker build -t <USUARIO>/auction-agent:latest .
docker push <USUARIO>/auction-agent:latest
kubectl apply -f agent-deployment.yaml
kubectl apply -f secret.yaml

cd ..
cd watcher
docker build -t <USUARIO>/auction-watcher:latest .
docker push <USUARIO>/auction-watcher:latest
kubectl apply -f watcher-deployment.yaml
```

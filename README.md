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

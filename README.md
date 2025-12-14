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

## Agente de IA
O código não foi testado porque tem um problema no meu python que possui certificados ssl desatualizados, que impedem a utilização da ferramenta de mandar e-mails e de instalar as bibliotecas necessárias para o Gemini funcionar.
A ferramenta de mandar mensagens pelo discord FUNCIONA, mas tem que atualizar o webhook do canal do discord que está no script

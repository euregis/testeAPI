# Documentação do TestAPI

## O que é o TestAPI?
O TestAPI é uma aplicação para criar, gerenciar e executar workflows de requisições HTTP. Ele permite definir passos (steps) com validações, dependências e configurações globais, facilitando a automação de testes e integrações.

## Funcionalidades principais:
- Criação e edição de workflows com múltiplos passos.
- Suporte a métodos HTTP (GET, POST, PUT, DELETE, PATCH).
- Validações automáticas de respostas (status, headers, body).
- Execução de passos com dependências.
- Interface web para gerenciar workflows.
- Execução via CLI com suporte a proxy.

---

## Requisitos

Certifique-se de ter os seguintes itens instalados:

- Python 3.8 ou superior
- Pip (gerenciador de pacotes do Python)
- Virtualenv (opcional, mas recomendado)

---

## Instalação

1. Clone o repositório:
   ```bash
   git clone <URL_DO_REPOSITORIO>
   cd TestAPI
   ```

2. Crie um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   source venv/bin/activate # No Windows: venv\Scripts\activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

---

## Como executar

### Executar o servidor web

1. Inicie o servidor Flask:
   ```bash
   python app.py
   ```

2. Acesse a interface web no navegador:
   ```
   http://localhost:5000
   ```

### Executar via CLI

1. Para executar todos os passos de um workflow:
   ```bash
   python exec.py workflow.json
   ```

2. Para executar um passo específico (e suas dependências):
   ```bash
   python exec.py workflow.json --step <NOME_DO_STEP>
   ```

3. Para executar com proxy:
   ```bash
   python exec.py workflow.json --use-proxy --http-proxy http://localhost:8080 --https-proxy http://localhost:8080
   ```

---

## Estrutura do Workflow

O arquivo `workflow.json` define os passos e configurações globais. Exemplo:

```json
{
  "workflowName": "ExemploWorkflow",
  "global": {
    "input": {
      "userId": "123",
      "token": "abc"
    }
  },
  "steps": {
    "get_user": {
      "method": "GET",
      "url": "https://api.example.com/users/${userId}",
      "headers": {
        "Authorization": "Bearer ${token}"
      },
      "validations": [
        { "target": "status", "operator": "equals", "value": 200 },
        { "target": "body.name", "operator": "notEmpty" }
      ]
    }
  }
}
```

---

## Explicação dos campos

- `target`: caminho para o valor na resposta (status, headers.<campo>, body.<campo>).
- `operator`: operador lógico:
  - `equals`
  - `notEquals`
  - `contains`
  - `notEmpty`
  - `greaterThan`
  - `lessThan`
  - `minLength`
  - `maxLength`
  - `isType`
  - `matchesRegex`
- `value`: valor comparativo (pode ser omitido em operadores como `notEmpty`).
- `stopOnFailure`: true/false para parar a execução da cadeia.

---

## Exemplos de uso

### Exemplo 1: Criar um workflow

1. Crie um arquivo `workflow.json` com o seguinte conteúdo:
   ```json
   {
     "workflowName": "MeuWorkflow",
     "global": {
       "input": {
         "userId": "123",
         "token": "abc"
       }
     },
     "steps": {
       "get_user": {
         "method": "GET",
         "url": "https://api.example.com/users/${userId}",
         "headers": {
           "Authorization": "Bearer ${token}"
         },
         "validations": [
           { "target": "status", "operator": "equals", "value": 200 },
           { "target": "body.name", "operator": "notEmpty" }
         ]
       }
     }
   }
   ```

2. Execute o workflow:
   ```bash
   python exec.py workflow.json
   ```

### Exemplo 2: Adicionar validações

Adicione validações para verificar o comprimento de um campo:
```json
{
  "target": "body.name",
  "operator": "minLength",
  "value": 3
}
```

---

## Contribuição

1. Faça um fork do repositório.
2. Crie uma branch para sua feature/bugfix:
   ```bash
   git checkout -b minha-feature
   ```
3. Faça commit das suas alterações:
   ```bash
   git commit -m "Descrição da alteração"
   ```
4. Envie suas alterações:
   ```bash
   git push origin minha-feature
   ```
5. Abra um Pull Request.

---

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

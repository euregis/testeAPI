##  Explicação dos campos:
 - `target`: caminho para o valor na resposta (status, headers.<campo>, body.<campo>).
 - `operator`: operador lógico:
    - `equals`
    - `notEquals`
    - `contains`
    - `notEmpty`
    - `greaterThan`
    - `lessThan`
 - `value`: valor comparativo (pode ser omitido em operadores como notEmpty).
 - `stopOnFailure`: true/false para parar a execução da cadeia.


# Executa todos os steps:
python main.py workflow.json

# Executa apenas o step `delete_todo` (e dependências):
python main.py workflow.json --step delete_todo

# Executa com proxy:
python main.py workflow.json --step delete_todo --use-proxy --http-proxy http://localhost:8080 --https-proxy http://localhost:8080

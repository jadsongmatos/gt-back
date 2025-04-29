## Template Python 3 HTTP para OpenFaaS

Um template oficial **python3-http-debian** para criar funções Python servidas via HTTP em OpenFaaS, baseado em Debian Bookworm (slim) e usando o of-watchdog para modo HTTP.

---

### 🚀 Visão Geral

- Ambiente completo para funções Python: Flask + Waitress + of-watchdog
- Base Debian (slim-bookworm) com toolchain para extensões nativas (NumPy, Pandas, Cryptography etc.)
- Multi-stage Dockerfile: `build` → `test` → `ship`

---

### 📋 Pré-requisitos

- **OpenFaaS CLI** (`faas-cli`) ≥ 0.18.2
- **Docker Engine** ou cluster Kubernetes (`faas-netes`)
- **Python 3.12+**
- **Git** (para clonar/pull do template)

---

### 📂 Estrutura de Arquivos

```bash
python3-http-debian/
├── Dockerfile          # Multi-stage para build, test e production
├── index.py            # Aplicação Flask + Waitress que delega ao handler
├── requirements.txt    # Dependências globais (flask, waitress, tox)
├── template.yml        # Definição do template para `faas-cli new`
└── function/
    ├── handler.py      # Seu código: função `def handle(event, context)`
    ├── requirements.txt# Dependências específicas da função
    ├── handler_test.py # Testes exemplo usando unittest ou pytest
    └── tox.ini         # Configuração de testes
```

---

### ⚙️ Uso Rápido

1. **Puxar o template**
   ```bash
   faas-cli template pull https://github.com/openfaas/templates.git
   ```
2. **Criar nova função**
   ```bash
   faas-cli new my-func --lang python3-http-debian
   cd my-func
   ```
3. **Implementar o handler** em `function/handler.py`
   ```python
   def handle(event, context):
       return {"statusCode": 200, "body": "Olá, OpenFaaS!"}
   ```
4. **Adicionar dependências** em `function/requirements.txt` e `requirements.txt`
5. **Build & Test**
   ```bash
   faas-cli build -f stack.yml       # roda stages build e test
   ```
6. **Push & Deploy**
   ```bash
   faas-cli push -f stack.yml
   faas-cli deploy -f stack.yml
   ```
7. **Invocar**
   ```bash
   echo -n "mundo" | faas-cli invoke my-func
   # Retorno: Olá, OpenFaaS!
   ```
8. **Iniciar Worker Celery**
   ```bash
   celery -A celery_app.celery worker --loglevel=info --concurrency=1
   ```

---

### 🔧 Configurações Avançadas

| ARG no Dockerfile       | Default           | Descrição                                        |
|-------------------------|-------------------|--------------------------------------------------|
| `PYTHON_VERSION`        | `3.12`            | Versão do Python                                 |
| `DEBIAN_OS`             | `slim-bookworm`   | Variante Debian                                  |
| `ADDITIONAL_PACKAGE`    | (vazio)           | Pacotes Debian extras (e.g., `libpq-dev`)        |
| `UPGRADE_PACKAGES`      | `false`           | Executar `apt-get upgrade`                       |
| `TEST_ENABLED`          | `true`            | Habilita stage `test`                            |
| `TEST_COMMAND`          | `tox`             | Comando para rodar testes                        |

**Variáveis de ambiente** no `stack.yml`:
```yaml
env:
  LOG_LEVEL: DEBUG
  CUSTOM_VAR: valor
```

**Build args** no `stack.yml`:
```yaml
build_args:
  PYTHON_VERSION: 3.12
```

---

### 🧪 Testes e Debug

- **Logs**:
  ```bash
  faas-cli logs my-func
  ```
- **Shell no container**:
  ```bash
  faas-cli exec -f stack.yml bash
  ```
- **Executar testes localmente**:
  ```bash
  tox
  ```

---

### ⚙️ Healthcheck

Por padrão:
```dockerfile
HEALTHCHECK --interval=5s CMD [ -e /tmp/.lock ] || exit 1
```
Você pode:
- Gravar `/tmp/.lock` no handler
- Ajustar o comando no Dockerfile

---

### 📖 Referências

- [Repositório de Templates OpenFaaS](https://github.com/openfaas/templates)
- [Template python3-http-debian](https://github.com/openfaas/templates/tree/master/template/python3-http-debian)
- [Documentação OpenFaaS](https://docs.openfaas.com)

# Docker - Projeto Raio

Este projeto pode rodar com Docker Compose para manter a mesma versao de Node, Python, Redis e dependencias em todos os dispositivos.

## Servicos

- `frontend`: Next.js em `http://localhost:3000`
- `backend`: FastAPI em `http://localhost:8000`
- `worker`: Celery para processar extracoes
- `redis`: fila Celery e estado dos jobs
- `backend-data`: volume persistente para `raio.db`, uploads e resultados

## Como subir

1. Copie o arquivo de ambiente:

```bash
copy .env.example .env
```

2. Ajuste `SECRET_KEY` no `.env`.

3. Suba tudo:

```bash
docker compose up --build
```

4. Acesse:

```text
http://localhost:3000
```

## ODA File Converter

A extracao de arquivos `.dwg` depende do ODA File Converter. No Docker, o sistema usa um wrapper interno:

```text
/usr/local/bin/oda-file-converter
```

Esse wrapper executa o binario real com `xvfb-run`, necessario para rodar o ODA/Qt dentro de container sem tela.

### Linux com ODA instalado via `.deb`

Depois de instalar o pacote ODA na VM, localize a pasta real:

```bash
sudo find / -type f -name "ODAFileConverter*" 2>/dev/null
```

Normalmente ela fica em:

```text
/usr/bin/ODAFileConverter_27.1.0.0
```

No `.env`, use:

```env
ODA_HOST_DIR=/usr/bin/ODAFileConverter_27.1.0.0
ODA_REAL_PATH=/opt/oda/ODAFileConverter
```

O Compose monta `ODA_HOST_DIR` como `/opt/oda` dentro dos containers.
O `ODA_PATH` usado pela aplicacao e fixado internamente como `/usr/local/bin/oda-file-converter`, para garantir que o wrapper com `xvfb-run` seja sempre usado.

### Pasta local `./oda`

Tambem e possivel colocar uma instalacao compativel em:

```text
projeto-raio-web/
  oda/
    ODAFileConverter
```

Nesse caso, mantenha:

```env
ODA_HOST_DIR=./oda
ODA_REAL_PATH=/opt/oda/ODAFileConverter
```

Observacao: se o conversor disponivel no seu computador for apenas `.exe` do Windows, ele nao roda dentro de um container Linux comum. Nesse caso, as opcoes sao:

- usar uma versao compativel com o sistema do container;
- rodar o processamento DWG em uma maquina Windows separada;
- ou usar Docker apenas para frontend, backend, Redis e Celery, mantendo a conversao DWG fora do container.

PDFs continuam sem depender do ODA.

## Portas

Por padrao:

```env
FRONTEND_PORT=3010
BACKEND_PORT=8000
```

Se a porta 3010 ja estiver ocupada, ajuste no `.env`:

```env
FRONTEND_PORT=3010
```

## Comandos uteis

Ver logs:

```bash
docker compose logs -f
```

Ver logs apenas do worker:

```bash
docker compose logs -f worker
```

Parar:

```bash
docker compose down
```

Parar e apagar volumes:

```bash
docker compose down -v
```

## Dados persistentes

O banco SQLite e arquivos gerados ficam no volume `backend-data`. Isso evita perder dados em rebuilds.

Para backup:

```bash
docker run --rm -v projeto-raio-web_backend-data:/data -v "%cd%:/backup" alpine tar czf /backup/backend-data-backup.tar.gz /data
```

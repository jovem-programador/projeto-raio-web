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

A extracao de arquivos `.dwg` depende do ODA File Converter.

No Compose, o caminho esperado dentro do container e:

```text
/opt/oda/ODAFileConverter
```

A pasta local `./oda` e montada como `/opt/oda` nos containers `backend` e `worker`.

Exemplo de estrutura:

```text
projeto-raio-web/
  oda/
    ODAFileConverter
```

Se voce usa outro caminho, ajuste no `.env`:

```env
ODA_PATH=/opt/oda/ODAFileConverter
```

Observacao: se o conversor disponivel no seu computador for apenas `.exe` do Windows, ele nao roda dentro de um container Linux comum. Nesse caso, as opcoes sao:

- usar uma versao compativel com o sistema do container;
- rodar o processamento DWG em uma maquina Windows separada;
- ou usar Docker apenas para frontend, backend, Redis e Celery, mantendo a conversao DWG fora do container.

PDFs continuam sem depender do ODA.

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

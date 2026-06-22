# FanSite Content Bot

Bot para Telegram pensado para fansites. Ele monitora artistas e envia alertas com textos prontos para X/Twitter, título para WordPress e categoria sugerida.

## Monitora

- Eventos e aparições públicas
- Celebrity sightings/candids
- Novos projetos
- Trailers e vídeos
- Entrevistas
- Capas/editoriais de revista
- Notícias de redes sociais

## Arquivos

- `monitor.py` — script principal
- `artists.txt` — lista editável de artistas
- `settings.json` — configurações
- `seen.json` — itens já vistos
- `.github/workflows/fansite-content-bot.yml` — GitHub Actions

## Secrets no GitHub

Settings → Secrets and variables → Actions → New repository secret

Crie:

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

## Frequência

Por padrão roda a cada 30 minutos:

```yaml
- cron: "*/30 * * * *"
```

## Primeira execução

Por padrão, a primeira execução salva itens antigos sem mandar spam. Para mudar isso, edite `settings.json`:

```json
"ignore_first_run_old_items": false
```

## Importante

O bot não baixa imagens/vídeos de Instagram ou bancos de imagem. Ele envia alertas, links e textos prontos para publicação.

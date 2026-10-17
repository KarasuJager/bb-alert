# bb-alert

Te llama por Telegram (y te manda un mensaje con los enlaces) cuando aparece un programa público nuevo en **HackerOne**, **Bugcrowd** o **YesWeHack**. Intigriti también está soportado si lo activas.

Funciona en GitHub Actions cada 15 min. Todo gratis.

## Cómo funciona

1. Descarga [arkadiyt/bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data), que se actualiza cada ~30 min con todos los programas públicos.
2. Compara con `seen.json` (programas ya vistos, se guarda en el propio repo).
3. Si hay alguno nuevo: mensaje de Telegram con nombre, plataforma, bounty máximo y enlace, y después una **llamada** de voz por Telegram vía CallMeBot.

La primera ejecución solo inicializa el estado; no te avisa de los ~800 programas existentes.
Si la fuente falla para una plataforma (lista vacía o muy corta), se ignora esa ejecución para no llamarte por error.

## Puesta en marcha (~10 min)

### 1. Repo en GitHub
Crea un repo **privado** (por ejemplo `bb-alert`) y sube estos archivos:
```
alert.py
.github/workflows/bb-alert.yml
```

### 2. Bot de Telegram (para el mensaje con enlaces)
1. Habla con **@BotFather** → `/newbot` → apunta el token.
2. Escríbele cualquier cosa a tu bot nuevo.
3. Abre `https://api.telegram.org/bot<TOKEN>/getUpdates` y copia `message.chat.id`. Ese es tu `TG_CHAT_ID`.

### 3. Llamada con CallMeBot
1. En Telegram: *Ajustes → Privacidad y seguridad → Llamadas*: permite que te llamen (o añade **@CallMeBot_API** a contactos si solo permites contactos).
2. Abre **@CallMeBot_txtbot** y pulsa *Start* para autorizarlo.
3. Pruébalo desde el navegador (cambia `@tuusuario`):
   `https://api.callmebot.com/start.php?user=@tuusuario&text=prueba&lang=es-ES-Standard-A`
   Si no funciona con el @usuario, usa tu teléfono en formato `+34XXXXXXXXX`.

### 4. Secrets del repo
*Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `TG_BOT_TOKEN` | token de BotFather |
| `TG_CHAT_ID` | tu chat id |
| `CALLMEBOT_USER` | `@tuusuario` o `+34...` |

### 5. Arrancar
En la pestaña **Actions**, activa los workflows si te lo pide, entra en *bb-alert* y pulsa **Run workflow**. Esa primera ejecución crea `seen.json`. A partir de ahí corre solo.

## Ajustes (en el `.yml`)

- `PLATFORMS: hackerone,bugcrowd,yeswehack,intigriti` para añadir Intigriti.
- `ONLY_BOUNTY: "1"` para que solo te avise de programas con recompensa (ignora los VDP).
- `cron`: frecuencia. La fuente se actualiza cada 30 min, así que bajar de 15 no aporta.

## Probar sin esperar a un programa nuevo
Borra una línea cualquiera de `seen.json` (por ejemplo un `"h1:..."`), haz commit y lanza el workflow a mano. Te debería llegar el mensaje y la llamada con ese programa.

En local:
```bash
git clone --depth 1 https://github.com/arkadiyt/bounty-targets-data.git btd
DRY_RUN=1 python3 alert.py   # no envía nada, solo imprime
```

## A tener en cuenta
- GitHub desactiva los workflows programados si el repo pasa **60 días sin actividad**. Los commits de `seen.json` cuentan como actividad y suele haber programas nuevos cada pocos días, pero si recibes el email de aviso, pulsa *Enable* en Actions.
- Los cron de GitHub pueden retrasarse unos minutos en horas punta.
- CallMeBot es un servicio gratuito de terceros, sin SLA. Si un día no llama, el mensaje del bot de Telegram llega igualmente.
- Solo detecta programas **públicos**. Las invitaciones privadas no aparecen en esta fuente; esas te llegan por email de cada plataforma.

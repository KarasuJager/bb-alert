# bb-alert

Te avisa al móvil con una **alarma (ntfy)** y un **mensaje de Telegram** cuando aparece un programa público nuevo en **HackerOne**, **Bugcrowd** o **YesWeHack**. Intigriti también está soportado si lo activas.

Funciona en GitHub Actions cada 15 min. Todo gratis.

## Cómo funciona

1. Descarga [arkadiyt/bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data), que se actualiza cada ~30 min con todos los programas públicos.
2. Compara con `seen.json` (programas ya vistos, se guarda en el propio repo).
3. Si hay alguno nuevo:
   - **Mensaje de Telegram** con nombre, plataforma, bounty máximo y enlace.
   - **Alarma de ntfy** con prioridad máxima (suena aunque estés en No molestar, si lo configuras así).
   - Opcionalmente, una **llamada de voz** por Telegram vía CallMeBot (ver más abajo).

La primera ejecución solo inicializa el estado; no te avisa de los ~800 programas existentes.
Si la fuente falla para una plataforma (lista vacía o muy corta), se ignora esa ejecución para no avisarte por error.

## Puesta en marcha (~10 min)

### 1. Repo en GitHub
Crea un repo (público recomendado, para no gastar minutos de Actions) con estos archivos:
```
alert.py
.github/workflows/bb-alert.yml
```

### 2. Bot de Telegram (para el mensaje con enlaces)
1. Habla con **@BotFather** → `/newbot` → apunta el token.
2. Abre tu bot nuevo y pulsa **Start** (imprescindible: un bot no puede escribirte hasta que tú le hablas).
3. Saca tu ID: busca **@userinfobot**, pulsa *Start* y apunta el número `Id`. Ese es tu `TG_CHAT_ID`.

### 3. Alarma con ntfy
1. Instala la app **ntfy** (Play Store / App Store).
2. Pulsa **+** y suscríbete a un tema secreto, p. ej. `bbalert-xxxxxxxx` (funciona como contraseña; no lo compartas).
3. Para que suene como alarma: en los ajustes de ntfy activa *"Keep alerting for highest priority"*, y en Android permite que la categoría de prioridad máxima **ignore No molestar**.
4. Pruébalo desde el navegador:
   `https://ntfy.sh/TU_TEMA/publish?message=prueba&priority=5`

### 4. (Opcional) Llamada con CallMeBot
CallMeBot es un servicio gratuito de terceros para recibir una llamada de voz por Telegram. **Es poco fiable** (colas y bloqueos frecuentes por "spam"), por eso la alarma principal es ntfy. Si quieres intentarlo:
1. En Telegram: *Ajustes → Privacidad y seguridad → Llamadas*: permite que te llamen.
2. Abre **@CallMeBot_txtbot** y pulsa *Start* para autorizarlo.
3. Prueba (cambia `@tuusuario`):
   `https://api.callmebot.com/start.php?user=@tuusuario&text=prueba&lang=es-ES-Standard-A`
4. Si te bloquea por spam, añade a contactos el bot que te indique (p. ej. `@CallMeBot_API16`) y escríbele.

Si no usas la llamada, simplemente no crees el secret `CALLMEBOT_USER`.

### 5. Secrets del repo
*Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Valor |
|---|---|
| `TG_BOT_TOKEN` | token de BotFather |
| `TG_CHAT_ID` | tu chat id |
| `NTFY_TOPIC` | tu tema de ntfy, p. ej. `bbalert-xxxxxxxx` |
| `CALLMEBOT_USER` | (opcional) `@tuusuario` o `+34...` |

### 6. Arrancar
En la pestaña **Actions**, activa los workflows si te lo pide, entra en *bb-alert* y pulsa **Run workflow**. Esa primera ejecución crea `seen.json`. A partir de ahí corre solo.

## Ajustes (en el `.yml`)

- `PLATFORMS: hackerone,bugcrowd,yeswehack,intigriti` para añadir Intigriti.
- `ONLY_BOUNTY: "1"` para que solo te avise de programas con recompensa (ignora los VDP).
- `cron`: frecuencia. La fuente se actualiza cada 30 min, así que bajar de 15 no aporta.

## Probar sin esperar a un programa nuevo
Borra una línea cualquiera de `seen.json` (por ejemplo un `"h1:..."`), haz commit y lanza el workflow a mano. Te deberían llegar la alarma y el mensaje con ese programa.

En local:
```bash
git clone --depth 1 https://github.com/arkadiyt/bounty-targets-data.git btd
DRY_RUN=1 python3 alert.py   # no envía nada, solo imprime
```

## A tener en cuenta
- GitHub desactiva los workflows programados si el repo pasa **60 días sin actividad**. Los commits de `seen.json` cuentan como actividad, pero si recibes el email de aviso, pulsa *Enable* en Actions.
- Los cron de GitHub pueden retrasarse unos minutos en horas punta.
- ntfy y CallMeBot son servicios gratuitos de terceros, sin SLA. El tema de ntfy es público para quien conozca el nombre: usa uno largo y aleatorio.
- Solo detecta programas **públicos**. Las invitaciones privadas no aparecen en esta fuente; esas te llegan por email de cada plataforma.

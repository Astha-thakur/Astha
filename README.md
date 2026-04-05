# TempAPI Bot

## Flow
/newkey → Original URL → Expiry → Temp Link ✅

## Kaise Kaam Karta Hai

Original URL:
https://devil-api.elementfx.com/api/num-info.php?key=@CYBER_AS&phone={phone}

Temp Link milega:
https://your-app.com/tapi-xxxx

Use karo:
https://your-app.com/tapi-xxxx?phone=919876543210

## Heroku Deploy

heroku create app-name
heroku config:set BOT_TOKEN="token"
heroku config:set MONGO_URI="mongodb+srv://..."
heroku config:set PROXY_URL="https://app-name.herokuapp.com"
git push heroku main
heroku ps:scale web=1

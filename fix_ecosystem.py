import re
with open("/www/wwwroot/wojiayun/ecosystem.config.js", "r") as f:
    content = f.read()
content = content.replace("PYTHONUNBUFFERED: '1'", "PYTHONUNBUFFERED: '1',\n        DB_HOST: '127.0.0.1',\n        DB_PASSWORD: 'Wojia2024!@#'")
with open("/www/wwwroot/wojiayun/ecosystem.config.js", "w") as f:
    f.write(content)
print("Done")
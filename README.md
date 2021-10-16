Script to monitor YouTube livestream chat

Requires a 'client_secrets.json' file in the same directory. Contents of this file should be:

```
{
    "API_KEY": "<api key here>"
}
```

Also run mongodb

```
docker pull mongo
docker run --rm -p 27017:27017 mongo:latest
```

"""Чат Twitch VOD через публичный GQL API (библиотека chat-downloader сломана с 2026 г.).

Usage: python download_chat.py <vod_id> <out.json>
Client-ID: TWITCH_CLIENT_ID из .env, иначе twitch.client_id из config.json.
Формат: [{time_in_seconds, message, author: {name}, emotes: [{name}]}]
"""
import json
import os
import sys
import time
import urllib.request

from common import config  # импорт common заодно загружает .env из корня проекта

GQL = "https://gql.twitch.tv/gql"
FIELDS = "edges{cursor node{contentOffsetSeconds commenter{displayName} message{fragments{text emote{emoteID}}}}} pageInfo{hasNextPage}"


def client_id():
    cid = os.environ.get("TWITCH_CLIENT_ID", "").strip() or config().get("twitch", {}).get("client_id", "")
    if not cid:
        sys.exit("ОШИБКА: нет Client-ID Twitch ни в .env, ни в config.json (twitch.client_id).")
    return cid


def gql(query):
    req = urllib.request.Request(
        GQL, data=json.dumps({"query": query}).encode(),
        headers={"Client-ID": client_id(), "Content-Type": "application/json"},
    )
    for attempt in range(5):
        try:
            return json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2**attempt)


def download(vod_id, out):
    messages, cursor = [], None
    while True:
        arg = f'after:"{cursor}"' if cursor else "contentOffsetSeconds:0"
        resp = gql(f'query{{video(id:"{vod_id}"){{comments({arg}){{{FIELDS}}}}}}}')
        video = (resp.get("data") or {}).get("video")
        comments = (video or {}).get("comments")
        if not comments:
            sys.exit(f"ОШИБКА: Twitch не отдал чат (VOD удалён/скрыт или Client-ID больше не принимается). "
                     f"Ответ: {resp.get('errors') or 'пусто'}")
        for edge in comments["edges"]:
            node = edge["node"]
            frags = node["message"]["fragments"]
            messages.append({
                "time_in_seconds": node["contentOffsetSeconds"],
                "message": "".join(f["text"] for f in frags),
                "author": {"name": (node["commenter"] or {}).get("displayName")},
                "emotes": [{"name": f["text"]} for f in frags if f["emote"]],
            })
        if not comments["pageInfo"]["hasNextPage"] or not comments["edges"]:
            break
        cursor = comments["edges"][-1]["cursor"]
    json.dump(messages, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    return len(messages)


if __name__ == "__main__":
    print(f"chat: {download(sys.argv[1], sys.argv[2])} messages")

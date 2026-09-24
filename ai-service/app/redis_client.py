"""Redis 连接的唯一来源:chat(会话状态)与 budget(路线成本估算缓存)共用。

三个坑集中在这里处理(原来写在 chat.py 里,出现第二个消费者后上移):
  1) 每次新建连接没必要 —— 复用一个 client。
  2) redis-py 8.x 默认带重试退避:只设 socket_connect_timeout 时 Redis 停机单次 get 要等
     27 秒(实测),每轮 load+save 就是 ~50 秒。retry=None + 短超时后降到每次 ~1 秒。
  3) `localhost` 会先试 IPv6(::1) 再试 IPv4,两次各等满一个 connect timeout,所以每次 op
     的实际代价是"超时 × 2" —— 默认超时因此取 0.5s 而不是 2s。

这里只负责给出一个**连不连得上都不会抛异常**的 client 句柄;get/set 的失败由调用方
自己接(chat 退本地镜像、budget 退进程内缓存),降级口径不统一反而会让故障表现不一致。
"""
from __future__ import annotations

import redis as redis_lib

from app.config import REDIS_HOST, REDIS_PORT, REDIS_SOCKET_TIMEOUT_SECONDS

_CLIENT: dict[str, redis_lib.Redis] = {}


def get_client() -> redis_lib.Redis:
    r = _CLIENT.get("r")
    if r is None:
        r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True,
                            socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
                            retry=None)
        _CLIENT["r"] = r
    return r

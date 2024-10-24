def parse_remote_host(host):
    user_host = host.split('@')[0] + '@' + host.split('@')[1].split(':')[0]
    port = host.split(':')[1] if ':' in host else None
    return user_host, port
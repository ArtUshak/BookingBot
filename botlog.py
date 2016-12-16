def log(msg, msgtype='NORMAL'):
    print('[%s] %s' % (msgtype, msg))
    if msgtype == 'ERROR':
        raise Exception('Bot error')

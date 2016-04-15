import simplejson as json
import websocket

from time import sleep

def navigate_to_page(debug_connection, url):
    '''
    Navigates to the url.
    '''
    navigate_to_page = json.dumps({ "id": 0, "method": "Page.navigate", "params": { "url": url }})
    debug_connection.send(navigate_to_page)
    sleep(1.0)

def reload_page(debug_connection, ignore_cache=True):
    '''
    Reloads the current page.
    '''
    reload_page = json.dumps({ "id": 1, "method": "Page.reload", "params": { "ignoreCache": ignore_cache }})
    debug_connection.send(reload_page)
    sleep(1.0)

def set_user_agent(debug_connection, user_agent_str):
    override_user_agent = json.dumps({ "id": 6, "method": "Network.setUserAgentOverride", "params": { "userAgent": user_agent_str }})
    debug_connection.send(override_user_agent)
    sleep(0.5)

def get_start_end_time_with_socket(ws):
    start_time = None
    end_time = None
    while start_time is None or end_time is None or (start_time is not None and start_time <= 0) or (end_time is not None and end_time <= 0):
        try:
            # print 'navigation starts: ' + str(navigation_starts)
            if start_time is None or start_time <= 0:
                navigation_starts = json.dumps({ "id": 6, "method": "Runtime.evaluate", "params": { "expression": "performance.timing.navigationStart", "returnByValue": True }})
                ws.send(navigation_starts)
                nav_starts_result = json.loads(ws.recv())
                # print 'start time: ' + str(nav_starts_result)
                start_time = int(nav_starts_result['result']['result']['value'])
            if end_time is None or end_time <= 0:
                load_event_ends = json.dumps({ "id": 6, "method": "Runtime.evaluate", "params": { "expression": "performance.timing.loadEventEnd", "returnByValue": True }})
                ws.send(load_event_ends)
                load_ends = json.loads(ws.recv())
                end_time = int(load_ends['result']['result']['value'])
        except Exception as e:
            pass
    return start_time, end_time

def get_start_end_time(debugging_url):
    # print 'debugging_url: ' + debugging_url
    ws = websocket.create_connection(debugging_url)
    return get_start_end_time_with_socket(ws)

def clear_cache(debug_connection):
    '''
    Clears the cache in the browser
    '''
    clear_cache = { "id": 4, "method": "Network.clearBrowserCache" }
    debug_connection.send(json.dumps(clear_cache))
    # result = json.loads(debug_connection.recv())
    # print result
    print 'Cleared browser cache'
    sleep(1.0)

def set_device_screen_size(debug_connection, screen_size_options, page_id):
    '''
    Sets the screen size options
    '''
    set_screen_size = { "method": "Page.setDeviceMetricsOverride" }
    set_screen_size['id'] = page_id
    set_screen_size['params'] = { \
        'width': screen_size_options['width'], \
        'height': screen_size_options['height'], \
        'deviceScaleFactor': screen_size_options['density'], \
        'mobile': screen_size_options['mobile'], \
        'fitWindow': screen_size_options['fitWindow'] \
        # 'fitWindow': screen_size_options['fitWindow'], \
        # 'screenWidth': screen_size_options['width'], \
        # 'screenHeight': screen_size_options['height'] \
    }
    print 'Setting screen size... ' + str(set_screen_size)
    debug_connection.send(json.dumps(set_screen_size))
    # result = json.loads(debug_connection.recv())
    # print result
    sleep(1.5)

import requests
import json
import urllib.parse
import time

base_api_url = 'https://glz.co.il/umbraco/api'

request_headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Connnection': 'keep-alive',
    'Host': 'glz.co.il',
    'User-Agent': 'HTTPie/0.9.8',
}

def parse_event(event):
    return event['path'], event['pathParameters']

def bad_request(message):
    return {
        'statusCode': 400,
        'body': json.dumps({
            'message': message
        })
    }

def handler(event, context):
    try:
        path, params = parse_event(event)
    except Exception as error:
        return bad_request(f'Got {type(error)} while parsing request: {error}')

    program_id = None

    if params:
        try:
            program_id = urllib.parse.quote(params['programId'])
        except:
            return bad_request('Failed to find program ID')

    supported_api_routes = {
        '/programmes': f'{base_api_url}/programme/GetProgrammesList',
        f'/program/{program_id}': f'{base_api_url}/programme/GetProgramme',
        '/schedule': f'{base_api_url}/timetable/getTimetable',
    }

    request_params = {}

    if path == '/schedule':
        request_params['slideIndex'] = '0'
    elif path == f'/program/{program_id}':
        request_params['urlname'] = urllib.parse.unquote(program_id)

    request_params['rootId'] = '1051'

    try:
        api_url = supported_api_routes[path]
    except:
        return bad_request(f'Route {path} isn\'t supported by this API')

    retries = 0

    while retries <= 3:
        response, success = execute_request(api_url, request_params, request_headers)
        response['headers'] = {'X-Sane-GLZ-API-Proxy-Retries': str(retries)}

        if success:
            break

        time.sleep(0.1)
        retries += 1

    return response

def execute_request(api_url, request_params, request_headers):
    try:
        response = requests.get(api_url, params=request_params, headers=request_headers)
    except Exception as error:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Failed to request from GLZ API: {error}'
            })
        }, False

    try:
        response.raise_for_status()
    except Exception as error:
        return {
            'statusCode': 503,
            'body': json.dumps({
                'message': f'Bad response from GLZ API: {error}'
            })
        }, False

    try:
        response_body = response.json()
    except Exception as error:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': f'Failed to parse JSON from GLZ API response: {error}',
                'responseHeaders': dict(response.headers),
                'responseBody': response.text,
                'requestHeaders': request_headers,
                'requestParams': request_params,
                'requestUrl': api_url,
            })
        }, False

    return {
        'statusCode': response.status_code,
        'body': json.dumps(response_body)
    }, True

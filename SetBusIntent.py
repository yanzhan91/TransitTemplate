import boto3
import os


def set_bus(user_id, bus_id, stop_id, preset):
    update_exp = 'SET #p = :b'
    user_table = boto3.resource('dynamodb').Table(os.environ['user_table'])
    response = user_table.update_item(
        Key={
            'user_id': user_id
        },
        UpdateExpression=update_exp,
        ExpressionAttributeNames={
            '#p': 'preset %s' % preset
        },
        ExpressionAttributeValues={
            ':b': {'bus_id': bus_id, 'stop_id': stop_id}
        }
    )['ResponseMetadata']
    if response['HTTPStatusCode'] != 200:
        raise Exception('Internal Error: Failed to update Users table')

if __name__ == '__main__':
    set_bus('123', '3', '3', 'Preset One')

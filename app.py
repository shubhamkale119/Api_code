import os
import boto3
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

### AWS credentialsA
AWS_REGION = 'ap-south-1'
ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

# Connect to EC2
ec2_client = boto3.client('ec2', region_name=AWS_REGION,
                          aws_access_key_id=ACCESS_KEY_ID,
                          aws_secret_access_key=SECRET_ACCESS_KEY)


# Print the value of AWS_ACCESS_KEY_ID environment variable
print("AWS_ACCESS_KEY_ID:", os.environ.get('AWS_ACCESS_KEY_ID'))

# Print the value of AWS_SECRET_ACCESS_KEY environment variable
print("AWS_SECRET_ACCESS_KEY:", os.environ.get('AWS_SECRET_ACCESS_KEY'))


########### Starting page of to create EC2 instance
@app.route('/')
def create_virtualmachine_aws():
    return "Create AWS EC2 Instance"


######## Create new EC2 Instance with AMI ID and EC2 Instance

@app.route('/launch_instance', methods=['POST', 'GET'])
def launch_instance():
    # Get parameters from query string
    ami_id = request.args.get('ami_id')
    instance_type = request.args.get('instance_type')
    count = request.args.get('count')
    key_name = request.args.get('key_name')

    # Create a key pair
    key_pair = ec2_client.create_key_pair(KeyName=key_name)
    
    # Save the private key to a file
    private_key = key_pair['KeyMaterial']
    key_file_path = f"{key_name}.pem"
    with open(key_file_path, 'w') as file:
        file.write(private_key)
    
    # Ensure the private key file has the correct permissions
    os.chmod(key_file_path, 0o400)

    # Launch EC2 instance
    response = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        MinCount=int(count),
        MaxCount=int(count),
        KeyName=key_name  # Use the created key pair
    )

    instance_id = response['Instances'][0]['InstanceId']
    
    # Describe instances and count running instances
    instances_response = ec2_client.describe_instances()
    running_instances = 0
    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running':
                running_instances += 1
    
    return jsonify({
        'message': 'Instance launched successfully',
        'instance_id': instance_id,
        'running_instances': running_instances,
        'key_file': key_file_path
    })


#### Endpoint to download the key pair file
@app.route('/download_key', methods=['GET'])
def download_key():
    key_file_path = request.args.get('key_file')
    if os.path.exists(key_file_path):
        return send_file(key_file_path, as_attachment=True)
    else:
        return jsonify({'message': 'Key file not found'}), 404


#############  Get the list of all EC2 Instances as well as based on its state running, Stopped and Terminated

@app.route('/list_instances', methods=['GET'])
def list_instances():
    # Get state from query parameters
    state_filter = request.args.get('state')

    # Describe instances
    instances_response = ec2_client.describe_instances()
    instances = []
    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            # Filter instances based on state if provided
            if state_filter:
                if instance['State']['Name'] == state_filter:
                    instance_info = {
                        'instance_id': instance['InstanceId'],
                        'instance_type': instance['InstanceType'],
                        'state': instance['State']['Name']
                    }
                    instances.append(instance_info)
            else:
                instance_info = {
                    'instance_id': instance['InstanceId'],
                    'instance_type': instance['InstanceType'],
                    'state': instance['State']['Name']
                }
                instances.append(instance_info)
    
    return jsonify({
        'instances': instances
    })

############ Get the information of instance based on its instance_ID
@app.route('/instance_info', methods=['GET'])
def instance_info():
    # Get instance ID from query parameters
    instance_id = request.args.get('instance_id')
    
    # Describe instance based on instance ID
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    if 'Reservations' in response:
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_info = {
                    'instance_id': instance['InstanceId'],
                    'instance_type': instance['InstanceType'],
                    'state': instance['State']['Name']
                }
                return jsonify(instance_info)
    return jsonify({'message': 'Instance not found'})

########### Delete EC2 instance based on its Instance_ID

@app.route('/delete_instance', methods=['DELETE','GET'])
def delete_instance():
    # Get instance ID from query parameters
    instance_id = request.args.get('instance_id')
    
    # Terminate instance based on instance ID
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    
    return jsonify({'message': 'Instance terminated'})

########   Delete all instances at a time

@app.route('/delete_all_instances', methods=['DELETE','GET'])
def delete_all_instances():
    # Describe instances
    instances_response = ec2_client.describe_instances()
    instance_ids = []
    for reservation in instances_response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    # Terminate all instances
    ec2_client.terminate_instances(InstanceIds=instance_ids)
    
    return jsonify({'message': 'All instances terminated'})

##### stop instance based on its Instance_id

@app.route('/stop_instance', methods=['PUT','GET'])
def stop_instance():
    # Get instance ID from request
    instance_id = request.args.get('instance_id')

    # Stop the instance
    ec2_client.stop_instances(InstanceIds=[instance_id])

    return jsonify({'message': 'Instance stopped successfully'})


##start instance based on its instance_id

@app.route('/start_instance', methods=['PUT','GET'])
def start_instance():
    # Get instance ID from request
    instance_id = request.args.get('instance_id')

    # Start the instance
    ec2_client.start_instances(InstanceIds=[instance_id])

    return jsonify({'message': 'Instance started successfully'})

### Terminate EC2 instance on instance_id

@app.route('/terminate_instance', methods=['DELETE','GET'])
def terminate_instance():
    # Get instance ID from request
    instance_id = request.args.get('instance_id')

    # Terminate the instance
    ec2_client.terminate_instances(InstanceIds=[instance_id])

    return jsonify({'message': 'Instance terminated successfully'})

##### modify ec2 instance_type after the stopping ec2 instance 

@app.route('/modify_instance_type', methods=['PUT','GET'])
def modify_instance_type():
    # Get instance ID and new instance type from request
    instance_id = request.args.get('instance_id')
    new_instance_type = request.args.get('new_instance_type')

    # Modify instance type
    ec2_client.modify_instance_attribute(
        InstanceId=instance_id,
        InstanceType={
            'Value': new_instance_type
        }
    )

    return jsonify({'message': 'Instance type modified successfully'})

##### Add or update ec2 instance tags after the stopping EC2 instance and give tags as in json format

@app.route('/update_instance_tags', methods=['PUT','GET'])
def update_instance_tags():
    # Get instance ID and new tags from request
    instance_id = request.args.get('instance_id')
    new_tags = request.json  # Assuming the request body contains the new tags in JSON format

    # Convert the dictionary of tags into a list of dictionaries
    tags_list = [{'Key': key, 'Value': value} for key, value in new_tags.items()]

    # Update instance tags
    ec2_client.create_tags(
        Resources=[instance_id],
        Tags=tags_list
    )

    return jsonify({'message': 'Instance tags updated successfully'})


if __name__ == '__main__':
    app.run(debug=True)

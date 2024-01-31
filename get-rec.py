import boto3

def find_records_in_route53(hosted_zone_id, search_value):
    # Initialize Route53 client
    client = boto3.client('route53')
    
    # Initialize variables
    next_record_name = None
    next_record_type = None
    
    while True:
        # Fetch DNS records
        if next_record_name and next_record_type:
            response = client.list_resource_record_sets(
                HostedZoneId=hosted_zone_id,
                StartRecordName=next_record_name,
                StartRecordType=next_record_type
            )
        else:
            response = client.list_resource_record_sets(
                HostedZoneId=hosted_zone_id
            )
        
        # Loop through each record set
        for record_set in response['ResourceRecordSets']:
            for record in record_set.get('ResourceRecords', []):
                if search_value in record['Value']:
                    print(f"Found matching record: {record_set['Name']} {record_set['Type']} {record['Value']}")
        
        # Check for more records
        if response['IsTruncated']:
            next_record_name = response['NextRecordName']
            next_record_type = response['NextRecordType']
        else:
            break

if __name__ == "__main__":
    hosted_zone_id = input("Enter the hosted zone ID: ")
    search_value = input("Enter the value to search for: ")
    
    find_records_in_route53(hosted_zone_id, search_value)

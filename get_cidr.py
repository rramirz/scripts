import boto3

def get_all_regions():
    """Get all available AWS regions."""
    ec2_client = boto3.client('ec2', region_name='us-east-1')
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    return regions

def get_vpc_cidrs_for_region(region):
    """Get all VPC CIDRs for a specific AWS region."""
    ec2_resource = boto3.resource('ec2', region_name=region)
    vpcs = ec2_resource.vpcs.all()
    cidr_blocks = []

    for vpc in vpcs:
        cidr_blocks.append(vpc.cidr_block)

    return cidr_blocks

if __name__ == "__main__":
    all_regions = get_all_regions()

    for region in all_regions:
        print(f"Getting VPC CIDRs for region {region}")
        vpc_cidrs = get_vpc_cidrs_for_region(region)

        if vpc_cidrs:
            print(f"VPC CIDRs for region {region}: {', '.join(vpc_cidrs)}")
        else:
            print(f"No VPCs found in region {region}")

import boto3
import requests
from collections import defaultdict
import argparse

def get_pricing_data(region='eu-west-1'):
    url = f"https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/{region}/index.json"
    response = requests.get(url)
    return response.json()

def get_instance_sku(pricing_data, instance_type):
    # Skip serverless instances
    if 'db.serverless' in instance_type:
        return None

    for product in pricing_data['products'].values():
        attributes = product.get('attributes', {})
        if (attributes.get('instanceType') == instance_type and
            attributes.get('servicecode') == 'AmazonRDS' and
            attributes.get('databaseEngine') == 'Aurora PostgreSQL' and
            attributes.get('storage') == 'EBS Only'):
            return product['sku']
    return None

def get_instance_price(pricing_data, sku):
    terms = pricing_data['terms']['OnDemand'].get(sku, {})
    for term_attributes in terms.values():
        for price_dimension in term_attributes['priceDimensions'].values():
            if price_dimension['unit'] == 'Hrs':
                return float(price_dimension['pricePerUnit']['USD'])
    return 0.0

def get_reserved_instance_price_and_upfront(pricing_data, sku, lease_contract_length="1yr", purchase_option="All Upfront"):
    reserved_terms = pricing_data['terms']['Reserved'].get(sku, {})
    upfront_cost = 0.0

    for term_attributes in reserved_terms.values():
        term_length = term_attributes['termAttributes'].get('LeaseContractLength')
        purchase_option_attr = term_attributes['termAttributes'].get('PurchaseOption')

        if term_length == lease_contract_length and purchase_option_attr == purchase_option:
            for price_dimension in term_attributes['priceDimensions'].values():
                if price_dimension['unit'] == 'Quantity':
                    upfront_cost = float(price_dimension['pricePerUnit']['USD'])

    return upfront_cost

def calculate_annual_savings(on_demand_price, upfront_cost, count):
    if on_demand_price is None or upfront_cost is None:
        return 0.0
    on_demand_annual_cost = on_demand_price * count * 720 * 12  # 720 hours per month * 12 months
    return on_demand_annual_cost - upfront_cost

def list_aurora_clusters(ignore_clusters=None, pricing_option='ondemand', region='eu-west-1'):
    instance_sizes_clusters = defaultdict(set)

    rds_client = boto3.client('rds', region_name=region)

    clusters = rds_client.describe_db_clusters()
    for cluster in clusters['DBClusters']:
        cluster_id = cluster['DBClusterIdentifier']
        if ignore_clusters and cluster_id in ignore_clusters:
            continue

        instances = rds_client.describe_db_instances(
            Filters=[{'Name': 'db-cluster-id', 'Values': [cluster_id]}]
        )
        for instance in instances['DBInstances']:
            instance_size = instance['DBInstanceClass']

            if 'serverless' in instance_size:
                continue

            instance_sizes_clusters[instance_size].add(cluster_id)

    pricing_data = get_pricing_data(region)

    if pricing_option == 'ondemand':
        format_string = "{:<20} {:<6} {:<25} {:<17} {:<25} {}"
        print(format_string.format("Instance Type", "Count", "SKU", "OnDemand/hr ($)", "OnDemand/year ($)", "Clusters Using This Type"))

        for instance_type, clusters in instance_sizes_clusters.items():
            sku = get_instance_sku(pricing_data, instance_type)
            on_demand_price_per_hour = get_instance_price(pricing_data, sku) if sku else 0.0
            total_on_demand_yearly_cost = on_demand_price_per_hour * len(clusters) * 720 * 12  # Yearly cost

            print(format_string.format(instance_type, len(clusters), sku,
                                      f"{on_demand_price_per_hour:.2f}", f"{total_on_demand_yearly_cost:.2f}",
                                      ", ".join(clusters)))
    else:  # Reserved pricing
        format_string = "{:<20} {:<6} {:<25} {:<35} {:<25} {}"
        print(format_string.format("Instance Type", "Count", "SKU", "Aggregated Upfront Cost ($)", "Annual Savings ($)", "Clusters Using This Type"))

        for instance_type, clusters in instance_sizes_clusters.items():
            sku = get_instance_sku(pricing_data, instance_type)
            upfront_cost_per_instance = get_reserved_instance_price_and_upfront(pricing_data, sku, "1yr", "All Upfront")
            total_upfront_cost = upfront_cost_per_instance * len(clusters)
            on_demand_price_per_hour = get_instance_price(pricing_data, sku) if sku else 0.0
            annual_savings = calculate_annual_savings(on_demand_price_per_hour, total_upfront_cost, len(clusters))

            print(format_string.format(instance_type, len(clusters), sku, 
                                      f"{total_upfront_cost:.2f}", f"{annual_savings:.2f}", 
                                      ", ".join(clusters)))

def parse_arguments():
    parser = argparse.ArgumentParser(description='List Aurora Clusters and Instance Types with Pricing Options')
    parser.add_argument('--ignore-cluster', type=str, help='Comma-separated list of clusters to ignore')
    parser.add_argument('--pricing-option', type=str, choices=['ondemand', 'reserved'], default='ondemand', help='Choose between ondemand or reserved pricing')
    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_arguments()
    ignore_clusters = args.ignore_cluster.split(',') if args.ignore_cluster else None
    list_aurora_clusters(ignore_clusters, args.pricing_option)


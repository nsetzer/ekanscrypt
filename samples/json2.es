# parse and output extended JSON natively
json_payload = {
    "fruit": [
        {"type": "apple", "inventory": 1k},    # 1000 apples
        {"type": "orange", "inventory": 500},  # 500 oranges
    ]
    "vegetables": [
        {"type": "ketchup", "inventory": 3.2k}  # 3200.0 ketchup
    ]
}
# prints the list of fruit
print(json_payload->fruit)
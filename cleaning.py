import json


def load_from_json(filename):
    return json.load(open(filename, 'r', encoding='utf-8-sig'))


def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8-sig') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def run():
    new_data = {}
    count = 0
    data = load_from_json('laws_only_stripped.json')
    for key in data:
        new_data[key] = {}
        for sub_key in data[key]:
            # if not "\nkterým se mění" in data[key][sub_key][:300]:
            if not "\nkterým se mění volební zákon" in data[key][sub_key][:300]:
                new_data[key][sub_key] = data[key][sub_key]
                count += 1
    print(count)
    save_to_json(new_data, 'laws_only_stripped_v2.json')


if __name__ == '__main__':
    run()

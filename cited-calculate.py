#* H-index Calculated process by ChatGPT - Ponlawat
#* Based of Concept: https://philoflanguage.wordpress.com/2020/06/26/h-index-%E0%B8%84%E0%B8%B7%E0%B8%AD%E0%B8%AD%E0%B8%B0%E0%B9%84%E0%B8%A3-%E0%B9%83%E0%B8%8A%E0%B9%89%E0%B8%97%E0%B8%B3%E0%B8%AD%E0%B8%B0%E0%B9%84%E0%B8%A3/
def calculate_h_index(publications):
    publications.sort(key=lambda x: x['citation'], reverse=True)
    h_index = 0

    for i, publication in enumerate(publications, start=1):
        if i <= publication['citation']:
            h_index = i
        else:
            break

    return h_index

data = [
    {"name": "book 1", "citation": 48},
    {"name": "book 2", "citation": 40},
    {"name": "book 3", "citation": 25},
    {"name": "book 4", "citation": 15},
    {"name": "book 5", "citation": 8},
    {"name": "book 6", "citation": 6},
    {"name": "book 7", "citation": 2},
    {"name": "book 8", "citation": 0},
    {"name": "book 9", "citation": 0},
]

h_index_result = calculate_h_index(data)
print(f"The h-index is: {h_index_result}")
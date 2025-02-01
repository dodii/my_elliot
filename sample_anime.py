from elliot.run import run_experiment
import pandas as pd

# url = "http://files.grouplens.org/datasets/movielens/ml-1m.zip"
# print(f"Getting Movielens 1Million from : {url} ..")
# response = requests.get(url)

# ml_1m_ratings = []

# print("Extracting ratings.dat ..")
# with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
#     for line in zip_ref.open("ml-1m/ratings.dat"):
#         ml_1m_ratings.append(str(line, "utf-8").replace("::", "\t"))

# print("Printing ratings.tsv to data/movielens_1m/ ..")

# os.makedirs("data/movielens_1m", exist_ok=True)
# with open("data/movielens_1m/dataset.tsv", "w") as f:
#     f.writelines(ml_1m_ratings)

import resource

my_limit = 64 * 1024 * 1024 * 1024

resource.setrlimit(resource.RLIMIT_AS, (my_limit, my_limit))

print("Starting the Elliot's Anime dataset experiment")

# run_experiment("config_files/experiments/tsvd_test.yml")

run_experiment("config_files/experiments/anime_42.yml")
run_experiment("config_files/experiments/anime_43.yml")
run_experiment("config_files/experiments/anime_44.yml")
run_experiment("config_files/experiments/anime_45.yml")
run_experiment("config_files/experiments/anime_46.yml")

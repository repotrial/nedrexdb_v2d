from nedrexdb.db.parsers import _get_file_location_factory
import pandas as pd

get_file_location = _get_file_location_factory("hippie")


def parse_perplexity_techinque_scores():
    method_scores_file = get_file_location("perplexity_scores")
    method_scores = pd.read_csv(method_scores_file, sep='\t', usecols=['methods', 'score'])
    method_scores_dict = dict(zip(method_scores['methods'], method_scores['score']))
    return method_scores_dict
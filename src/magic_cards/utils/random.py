import random


def weighted_choice(choices):
    """
    Return a single element from a weighted sample.

    `choices` is a dictionary with labels (buckets) as keys and weights (probabilities) as values.
    """
    total = sum(choices.values())
    r = random.uniform(0, total)
    items = sorted(choices.items(), key=lambda x: x[1])
    for bucket, weight in items:
        r -= weight
        if r <= 0:
            return bucket

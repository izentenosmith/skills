import os

import meilisearch

_client = meilisearch.Client(
    os.environ["MEILI_URL"],
    os.environ.get("MEILI_MASTER_KEY") or None,
)

PRODUCTS = "products"


def find_products(term, limit=20):
    return _client.index(PRODUCTS).search(term, {"limit": limit})["hits"]


def reindex(products):
    return _client.index(PRODUCTS).add_documents(products, primary_key="sku")

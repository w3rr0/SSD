# Data

## Olist (Kaggle)

Source: "Brazilian E-Commerce Public Dataset by Olist"
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Download it and put these two files in `data/raw/`:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`

Easiest, from the repository root:

    uv run data/download_olist.py

Or with the Kaggle CLI:

    kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip

`data/raw/` is in `.gitignore`; the data is not committed
(size and the dataset's Kaggle licence).

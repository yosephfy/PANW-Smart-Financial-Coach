#!/usr/bin/env python3
"""Run a few sample predictions using the trained ai_categorizer model for u_demo"""
import sys
from pathlib import Path
import json
repo = Path(__file__).resolve().parents[2]
app_dir = Path(__file__).resolve().parent.parent / 'app'
print('DEBUG app_dir:', app_dir)
sys.path.insert(0, str(app_dir))

try:
    from ai_categorizer import predict_for_user, model_path
except Exception as e:
    print('Import error:', e)
    raise


def run_sample(user='u_demo'):
    print('Model path:', model_path(user))
    print('Model exists:', model_path(user).exists())
    samples = [
        ('Starbucks', 'STARBUCKS 1234'),
        ('Spotify', 'Spotify Premium Subscription'),
        ('Shell', 'Fuel purchase'),
    ]
    for merchant, desc in samples:
        print('\nINPUT -> merchant:', merchant, 'description:', desc)
        try:
            out = predict_for_user(user, merchant, desc, top_k=3)
            print(json.dumps(out, indent=2))
        except Exception as e:
            print('Prediction error:', e)


if __name__ == '__main__':
    run_sample()

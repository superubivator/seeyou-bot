#!/bin/bash
echo "Установка зависимостей..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

#!/bin/bash

echo "---
layout: default
title: "$1"
permalink: :path 
mathjax: true
---" > $2/$1.md

jupyter nbconvert --to markdown "$2/$1.ipynb" --output "data"

echo "Creating finale file" | cat $2/data.md >> $2/$1.md

rm "$2/data.md"
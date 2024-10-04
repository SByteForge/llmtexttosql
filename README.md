# Text to SQL Application

## Overview

This project aims to create a **Text to SQL** application that converts natural language queries into SQL queries to retrieve data from a MySQL database. The application leverages a large language model (LLM) to understand user input and generate appropriate SQL queries, allowing users to perform simple to complex data analysis tasks effortlessly.

## Features

- Convert natural language queries into SQL.
- Retrieve and display results from a MySQL database.
- Handle various types of queries, from simple selections to complex joins and aggregations.
- User-friendly interface for seamless interaction.

## Folder Structure

- `src/`: Contains the source code for the application.
  - `main.py`: The entry point for running the application.
  - `database.py`: Handles database connections and query execution.
  - `llm.py`: Manages interactions with the language model.
  - `utils.py`: Contains utility functions to assist with various tasks.
- `tests/`: Contains unit tests for the application.
- `requirements.txt`: Lists the necessary dependencies for the project.
- `config.yaml`: Configuration file for database credentials and settings.
- `.gitignore`: Specifies files and directories to be ignored by Git.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/text-to-sql-app.git
   cd text-to-sql-app

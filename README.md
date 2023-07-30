# Health Halo Backend

Demo from the Anthropic Hackathon 2023-07-30

## Installation instructions

### Prerequisites

- Python 3.11
- Poetry

### Steps

```bash
poetry install
poetry shell
```

### Configuration

We are connecting to the 'clinical' db.

Right now it contains lab_data, notes_data

Copy the .env.example => .env
It contains DB credentials but you need to put in your Anthropic API KEY.

**API KEY should not be rate limited**

### How to run

```bash
python server.py
```

## Scratch

### Function definition syntax

```xml
<function>
<function_name>get_current_temp</function_name>
<function_description>Gets the current temperature for a given city.</function_description>
<required_argumen>city (str): The name of the city to get the temperature for.</required_argument>
<returns>int: The current temperature in degrees Fahrenheit.</returns>
<raises>ValueError: If city is not a valid city name.</raises>
<example_call>get_current_temp(city="New York")</example_call>
</function>
```

in other words, python dict

```python
functions = [{
  "name": "get_current_temp",
  "description": "Gets the current temperature for a given city",
  "required_argument": "city (str): The name of the city to get the temperature for.",
  "returns":"int: The current tempareture in degrees Farenheight.",
  "raises": "ValueError: If city is not a valid city name.",
  "example_call": "get_current_temp(city=\"New York\")"
}]
```

This is a simple markup language combining aspects of BBCode and Markdown, designed for writing fanfics in a format that's flexible but that remains 'plain'.

## Usage

```
usage: render.py [-h] [--output OUTPUT] [--template TEMPLATE] [--config CONFIG] [source]

Render a markup file to HTML

positional arguments:
  source                input file; reads from stdin if omitted

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        output file; writes to stdout if omitted
  --template TEMPLATE, -t TEMPLATE
                        HTML template file with {{content}} placeholder
  --config CONFIG, -c CONFIG
                        JSON config file
```

The generated HTML relies on CSS styling to display correctly. The stylesheet `style.css` is provided as an example.

## Config

The configuration file allows the user to customise aspects of the rendering. `config.json` in this repo is provided as an example and doesn't represent the defaults.

```json
{
  "section_break_tag": "p",
  "section_break_class": "section-break",
  "section_break_text": "✱ ✱ ✱",

  "minor_section_break_tag": "p",
  "minor_section_break_class": "minor-section-break",
  "minor_section_break_text": "",

  "not_inset_class": "not-inset",
  "small_caps_class": "small-caps",
  "dialog_space_class": "fwsp"
}
```


---

More input-output example pairs are provided in the `examples` directory.

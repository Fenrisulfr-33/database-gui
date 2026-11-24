"""Convert between our simplified schema (a list of fields) and MongoDB's
`$jsonSchema` validator format.

No pymongo calls live here: this module only builds and checks plain dicts,
so the GUI (through MongoConnection) and the tests can both use it. The rules
it enforces are the ones in expected-behavior.md > Documents Page > Schema.

Author: Archer
"""

from dataclasses import dataclass

# The value types a field (or an array's items) can have. These are MongoDB's
# own `bsonType` names, so they can go straight into the $jsonSchema.
FIELD_TYPES = (
    "string", "int", "long", "double", "decimal", "bool", "date", "objectId",
)
NUMBER_TYPES = ("int", "long", "double", "decimal")

# Which $jsonSchema keywords hold the min/max for each kind of field.
STRING_LIMITS = ("minLength", "maxLength")
NUMBER_LIMITS = ("minimum", "maximum")
ARRAY_LIMITS = ("minItems", "maxItems")

# Top-level keys a schema may have and still fit the simplified view.
TOP_LEVEL_KEYS = {"bsonType", "required", "additionalProperties", "properties"}


class UnsupportedSchemaError(ValueError):
    """The schema uses something the simplified view can't show yet
    (nested objects, regex patterns, allowed-value lists, ...).

    Author: Archer
    """


@dataclass
class SchemaField:
    """One row of the simplified schema view.

    `minimum`/`maximum` mean string length, number value, or array item count
    depending on the field. None means "no limit".

    Author: Archer
    """

    name: str
    type: str
    required: bool = False
    is_array: bool = False
    minimum: int | float | None = None
    maximum: int | float | None = None


def build_schema(fields: list[SchemaField]) -> dict:
    """Turn the simplified field list into a strict $jsonSchema dict.

    Strict means no extra fields are allowed (`additionalProperties: false`).
    `_id` is always allowed so documents can still be inserted.
    Raises ValueError if a field breaks the rules.

    Author: Archer
    """
    _check_unique_names(fields)
    properties = {"_id": {}}
    for field in fields:
        _check_field(field)
        properties[field.name.strip()] = _field_to_property(field)
    schema = {"bsonType": "object", "additionalProperties": False,
              "properties": properties}
    required = [field.name.strip() for field in fields if field.required]
    if required:
        schema["required"] = required
    return schema


def parse_schema(schema: dict) -> list[SchemaField]:
    """Turn a $jsonSchema dict back into the simplified field list.

    Raises UnsupportedSchemaError if the schema uses anything the simplified
    view can't represent, so it's never saved half-understood.

    Author: Archer
    """
    _check_top_level(schema)
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    missing = [name for name in required if name not in properties]
    if missing:
        raise UnsupportedSchemaError(
            f"Required field(s) not defined in properties: {', '.join(missing)}.")
    fields = []
    for name, spec in properties.items():
        if name == "_id" and spec == {}:
            continue  # the "allow any _id" entry build_schema always adds
        fields.append(_property_to_field(name, spec, name in required))
    return fields


def _check_unique_names(fields: list[SchemaField]) -> None:
    """Raise ValueError if two fields share a name.

    Author: Archer
    """
    names = [field.name.strip() for field in fields]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Duplicate field name(s): {', '.join(duplicates)}.")


def _check_field(field: SchemaField) -> None:
    """Raise ValueError if one field's name, type, or limits are invalid.

    Author: Archer
    """
    name = field.name.strip()
    if not name:
        raise ValueError("Every field needs a name.")
    if name.startswith("$") or "." in name:
        raise ValueError(
            f"Field '{name}' can't start with '$' or contain '.'.")
    if field.type not in FIELD_TYPES:
        raise ValueError(f"Field '{name}' has an unknown type '{field.type}'.")
    if field.minimum is None and field.maximum is None:
        return
    if _limit_keys(field) is None:
        raise ValueError(f"Field '{name}' ({field.type}) can't have a min/max.")
    _check_limits(field)


def _check_limits(field: SchemaField) -> None:
    """Raise ValueError if min/max are the wrong kind of number or reversed.

    Author: Archer
    """
    counts = field.is_array or field.type == "string"
    for value in (field.minimum, field.maximum):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Field '{field.name}' min/max must be numbers.")
        if counts and (not isinstance(value, int) or value < 0):
            raise ValueError(
                f"Field '{field.name}' min/max must be whole numbers, 0 or more.")
    if None not in (field.minimum, field.maximum) and field.minimum > field.maximum:
        raise ValueError(f"Field '{field.name}' min is bigger than its max.")


def _limit_keys(field: SchemaField) -> tuple[str, str] | None:
    """Which $jsonSchema keywords hold this field's min/max (None = no limits).

    Author: Archer
    """
    if field.is_array:
        return ARRAY_LIMITS
    if field.type == "string":
        return STRING_LIMITS
    if field.type in NUMBER_TYPES:
        return NUMBER_LIMITS
    return None


def _field_to_property(field: SchemaField) -> dict:
    """Build the $jsonSchema property for one field.

    Optional fields also accept null, e.g. {"bsonType": ["string", "null"]}.
    Arrays hold one strict type: {"bsonType": "array", "items": {...}}.

    Author: Archer
    """
    outer_type = "array" if field.is_array else field.type
    spec = {"bsonType": outer_type if field.required else [outer_type, "null"]}
    if field.is_array:
        spec["items"] = {"bsonType": field.type}
    keys = _limit_keys(field)
    for key, value in zip(keys or (), (field.minimum, field.maximum)):
        if value is not None:
            spec[key] = value
    return spec


def _check_top_level(schema: dict) -> None:
    """Raise UnsupportedSchemaError unless the schema is a strict, flat object.

    Author: Archer
    """
    if not isinstance(schema, dict):
        raise UnsupportedSchemaError("A schema must be a JSON object.")
    extra = set(schema) - TOP_LEVEL_KEYS
    if extra:
        raise UnsupportedSchemaError(
            f"Unsupported in this version: {', '.join(sorted(extra))}.")
    if schema.get("bsonType", "object") != "object":
        raise UnsupportedSchemaError('The schema\'s bsonType must be "object".')
    if schema.get("additionalProperties") is not False:
        raise UnsupportedSchemaError(
            'Schemas must be strict: set "additionalProperties": false.')
    if not isinstance(schema.get("properties", {}), dict):
        raise UnsupportedSchemaError('"properties" must be a JSON object.')
    if not isinstance(schema.get("required", []), list):
        raise UnsupportedSchemaError('"required" must be a list of names.')


def _property_to_field(name: str, spec: dict, required: bool) -> SchemaField:
    """Turn one $jsonSchema property back into a SchemaField.

    Author: Archer
    """
    if not isinstance(spec, dict):
        raise UnsupportedSchemaError(f"Field '{name}' must be a JSON object.")
    outer_type = _outer_type(name, spec.get("bsonType"), required)
    is_array = outer_type == "array"
    value_type = _items_type(name, spec) if is_array else outer_type
    field = SchemaField(name, value_type, required, is_array)
    keys = _limit_keys(field) or ()
    allowed = {"bsonType", *keys} | ({"items"} if is_array else set())
    extra = set(spec) - allowed
    if extra:
        raise UnsupportedSchemaError(
            f"Field '{name}' uses unsupported rule(s): {', '.join(sorted(extra))}.")
    if keys:
        field.minimum, field.maximum = spec.get(keys[0]), spec.get(keys[1])
    _check_parsed(field)
    return field


def _outer_type(name: str, bson_type, required: bool) -> str:
    """Read a property's bsonType, checking null matches required.

    Required fields: a single type. Optional fields: [type, "null"].

    Author: Archer
    """
    if required and isinstance(bson_type, str):
        found = bson_type
    elif not required and isinstance(bson_type, list) and len(bson_type) == 2 \
            and "null" in bson_type:
        found = next(item for item in bson_type if item != "null")
    elif required:
        raise UnsupportedSchemaError(
            f"Required field '{name}' must have exactly one bsonType (no null).")
    else:
        raise UnsupportedSchemaError(
            f'Optional field \'{name}\' must allow null, e.g. ["string", "null"].')
    if found != "array" and found not in FIELD_TYPES:
        raise UnsupportedSchemaError(
            f"Field '{name}' has unsupported type '{found}'.")
    return found


def _items_type(name: str, spec: dict) -> str:
    """Read the single type an array field holds (no mixed or nested arrays).

    Author: Archer
    """
    items = spec.get("items")
    if not isinstance(items, dict) or set(items) != {"bsonType"} \
            or items["bsonType"] not in FIELD_TYPES:
        raise UnsupportedSchemaError(
            f"Array field '{name}' needs \"items\": {{\"bsonType\": <one type>}}.")
    return items["bsonType"]


def _check_parsed(field: SchemaField) -> None:
    """Re-use build_schema's field rules, reported as unsupported.

    Author: Archer
    """
    try:
        _check_field(field)
    except ValueError as error:
        raise UnsupportedSchemaError(str(error)) from error

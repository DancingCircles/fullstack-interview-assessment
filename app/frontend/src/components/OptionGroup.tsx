import type { ProductOption, Selection, Sku } from "../api/types";
import { isChoicePossible } from "../domain/variants";

interface OptionGroupProps {
  option: ProductOption;
  skus: Sku[];
  selection: Selection;
  onChange: (value: string) => void;
}

export function OptionGroup({ option, skus, selection, onChange }: OptionGroupProps) {
  return (
    <fieldset className="option-group">
      <legend>
        {option.label}
        {selection[option.id] ? <span className="selected-option">: {selection[option.id]}</span> : null}
      </legend>
      <div className="option-values" role="group" aria-label={option.label}>
        {option.values.map((value) => {
          const selected = selection[option.id] === value;
          const possible = isChoicePossible(skus, selection, option.id, value);
          return (
            <button
              className={`option-button ${option.id === "color" ? "colour" : "size"}`}
              type="button"
              key={value}
              aria-pressed={selected}
              disabled={!possible}
              onClick={() => onChange(value)}
            >
              {option.id === "color" ? <span className={`swatch ${value.toLowerCase()}`} aria-hidden="true" /> : null}
              {value}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

import { useState } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";

interface PasswordFieldProps {
  id: string;
  autoComplete: "current-password" | "new-password";
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
}

export function PasswordField({
  id,
  autoComplete,
  value,
  onChange,
  placeholder,
  required = true,
  minLength,
  maxLength,
  pattern,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span className="input-wrap password-input-wrap">
      <LockKeyhole size={17} aria-hidden="true" />
      <input
        id={id}
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
        autoCapitalize="none"
        autoCorrect="off"
        spellCheck={false}
        required={required}
        minLength={minLength}
        maxLength={maxLength}
        pattern={pattern}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
      <button
        type="button"
        className="password-toggle"
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        aria-controls={id}
        onClick={() => setVisible((current) => !current)}
      >
        {visible ? <EyeOff size={17} /> : <Eye size={17} />}
      </button>
    </span>
  );
}

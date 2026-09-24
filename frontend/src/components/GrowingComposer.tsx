import { FormEvent, KeyboardEvent, useLayoutEffect, useRef, useState } from "react";
import send from "../assets/corg/send.svg";

type GrowingComposerProps = {
  ariaLabel: string;
  className?: string;
  onSubmit?: (question: string) => void;
};

export function GrowingComposer({ ariaLabel, className = "", onSubmit }: GrowingComposerProps) {
  const [value, setValue] = useState("");
  const textarea = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    if (!textarea.current) return;
    textarea.current.style.height = "0";
    textarea.current.style.height = `${textarea.current.scrollHeight}px`;
  }, [value]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const question = value.trim();
    if (!question) return;
    onSubmit?.(question);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return <form className={`composer ${className}`} onSubmit={submit}>
    <textarea ref={textarea} rows={1} value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={handleKeyDown} placeholder="What do you want to know?" aria-label={ariaLabel} />
    <button aria-label="Send question"><img src={send} alt="" /></button>
  </form>;
}

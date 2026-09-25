import { ChangeEvent, FormEvent, KeyboardEvent, useLayoutEffect, useRef, useState } from "react";
import paperclip from "../assets/corg/paperclip.svg";
import send from "../assets/corg/send.svg";

type GrowingComposerProps = {
  ariaLabel: string;
  className?: string;
  documentCount?: number;
  uploadPending?: boolean;
  onDocumentsClick?: () => void;
  onFilesSelected?: (files: File[]) => void;
  onSubmit?: (question: string) => void;
};

export function GrowingComposer({ ariaLabel, className = "", documentCount = 0, uploadPending = false, onDocumentsClick, onFilesSelected, onSubmit }: GrowingComposerProps) {
  const [value, setValue] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
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

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length) onFilesSelected?.(files);
    event.target.value = "";
  };

  const handleDocumentsClick = () => {
    if (documentCount > 0) onDocumentsClick?.();
    else fileInput.current?.click();
  };

  return <form className={`composer ${className}`} onSubmit={submit}>
    <textarea ref={textarea} rows={1} value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={handleKeyDown} placeholder="What do you want to know?" aria-label={ariaLabel} />
    <input ref={fileInput} className="composer-file-input" type="file" accept=".pdf,.txt" multiple onChange={handleFiles} />
    <div className="composer-actions">
      <button className={`document-button${documentCount ? " active" : ""}`} type="button" aria-label={documentCount ? `${documentCount} documents selected` : "Attach documents"} onClick={handleDocumentsClick} disabled={uploadPending}>
        <img src={paperclip} alt="" />
        {documentCount > 0 && <span>{documentCount}</span>}
      </button>
      <button className="send-button" aria-label="Send question"><img src={send} alt="" /></button>
    </div>
  </form>;
}

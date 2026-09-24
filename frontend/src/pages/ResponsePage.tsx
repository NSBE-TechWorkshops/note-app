import { GrowingComposer } from "../components/GrowingComposer";

export function ResponsePage() {
  return <main className="reference-page">
    <button className="menu-button" aria-label="Open sidebar"><span /><span /><span /></button>
    <section className="reference-conversation">
      <p className="question">Can you explain the notes I uploaded?</p>
      <article className="answer"><p>Sure. The main idea is that Note Buddy reads your course documents, retrieves the relevant passages, and answers from those sources so you can trace every response back to your notes.</p></article>
    </section>
    <GrowingComposer className="docked" ariaLabel="Ask another question" />
  </main>;
}

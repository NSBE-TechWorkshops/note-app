import back from "../assets/corg/back.svg";
import { GrowingComposer } from "../components/GrowingComposer";

export function ConversationPage() {
  return <main className="reference-page">
    <button className="menu-button" aria-label="Back"><img src={back} alt="" /></button>
    <section className="reference-conversation detail-conversation">
      <div className="turn"><p className="question">Summarize chapter 4 in plain English.</p><article className="answer"><p>Chapter 4 explains how repeated practice turns fragile memory into knowledge that is easier to retrieve.</p></article></div>
      <div className="turn"><p className="question">Give me three study questions.</p><article className="answer"><p>1. What is the chapter's central claim?<br />2. Which example best supports it?<br />3. How would you apply the idea in a new context?</p></article></div>
    </section>
    <GrowingComposer className="docked" ariaLabel="Ask another question" />
  </main>;
}

import { Fragment, type ReactNode } from "react";

/**
 * Rendu du sous-ensemble Markdown produit par l'AI Writer : titres, listes,
 * citations, gras et italique. Aucune dépendance externe, et surtout aucun
 * `dangerouslySetInnerHTML` — le contenu vient d'un modèle de langage et ne
 * doit jamais pouvoir injecter de HTML dans la page.
 */

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let index = 0;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${keyPrefix}-i${index++}`;
    if (token.startsWith("**")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      nodes.push(
        <code key={key} className="rounded bg-ink-800 px-1 py-0.5 text-[13px]">
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export function Markdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const blocks: ReactNode[] = [];

  let bullets: string[] = [];
  let ordered: string[] = [];
  let paragraph: string[] = [];
  let quote: string[] = [];
  let key = 0;

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(<p key={`p${key++}`}>{renderInline(paragraph.join(" "), `p${key}`)}</p>);
      paragraph = [];
    }
  };
  const flushBullets = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul${key++}`}>
          {bullets.map((item, index) => (
            <li key={index}>{renderInline(item, `ul${key}-${index}`)}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  };
  const flushOrdered = () => {
    if (ordered.length) {
      blocks.push(
        <ol key={`ol${key++}`}>
          {ordered.map((item, index) => (
            <li key={index}>{renderInline(item, `ol${key}-${index}`)}</li>
          ))}
        </ol>,
      );
      ordered = [];
    }
  };
  const flushQuote = () => {
    if (quote.length) {
      blocks.push(
        <blockquote key={`bq${key++}`}>
          {quote.map((item, index) => (
            <Fragment key={index}>
              {renderInline(item, `bq${key}-${index}`)}
              {index < quote.length - 1 ? <br /> : null}
            </Fragment>
          ))}
        </blockquote>,
      );
      quote = [];
    }
  };
  const flushAll = () => {
    flushParagraph();
    flushBullets();
    flushOrdered();
    flushQuote();
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();

    if (!trimmed) {
      flushAll();
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      flushAll();
      const level = heading[1].length;
      const text = renderInline(heading[2], `h${key}`);
      const Tag = (["h1", "h2", "h3", "h4"] as const)[level - 1];
      blocks.push(<Tag key={`h${key++}`}>{text}</Tag>);
      continue;
    }

    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      flushAll();
      blocks.push(<hr key={`hr${key++}`} />);
      continue;
    }

    if (trimmed.startsWith(">")) {
      flushParagraph();
      flushBullets();
      flushOrdered();
      quote.push(trimmed.replace(/^>\s?/, ""));
      continue;
    }

    const bullet = trimmed.match(/^[-*•]\s+(.*)$/);
    if (bullet && !trimmed.startsWith("**")) {
      flushParagraph();
      flushOrdered();
      flushQuote();
      bullets.push(bullet[1]);
      continue;
    }

    const numbered = trimmed.match(/^\d+[.)]\s+(.*)$/);
    if (numbered) {
      flushParagraph();
      flushBullets();
      flushQuote();
      ordered.push(numbered[1]);
      continue;
    }

    flushBullets();
    flushOrdered();
    flushQuote();
    paragraph.push(trimmed);
  }

  flushAll();

  return <div className="prose-doc">{blocks}</div>;
}

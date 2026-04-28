export function JsonLd() {
  const schemas = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": "https://storemd.vercel.app/#organization",
        "name": "StoreMD",
        "url": "https://storemd.vercel.app",
        "logo": {
          "@type": "ImageObject",
          "url": "https://storemd.vercel.app/og-image.png",
          "width": 1200,
          "height": 630
        },
        "description": "AI agent that monitors Shopify store health 24/7. Replaces 5 apps with one — SEO, speed, accessibility, broken links, audit. Free preview scan available.",
        "foundingDate": "2025",
        "founder": {
          "@type": "Organization",
          "name": "FoundryTwo"
        },
        "contactPoint": {
          "@type": "ContactPoint",
          "email": "[contact@altidigitech.com](mailto:contact@altidigitech.com)",
          "contactType": "customer support"
        },
        "sameAs": []
      },
      {
        "@type": "SoftwareApplication",
        "@id": "https://storemd.vercel.app/#software",
        "name": "StoreMD",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "description": "AI-powered Shopify app that monitors store health 24/7. Detects ghost billing, app impact, code residue, SEO issues, broken links, and accessibility problems. Auto-fixes included.",
        "url": "https://storemd.vercel.app",
        "screenshot": "https://storemd.vercel.app/og-image.png",
        "featureList": "Free Preview Scan, Ghost Billing Detection, App Impact Analysis, Code Residue Scanner, Listing Optimizer, Auto-Fix Engine, 24/7 Monitoring, Real Browser Testing",
        "offers": [
          {
            "@type": "Offer",
            "name": "Free",
            "price": "0",
            "priceCurrency": "USD",
            "priceValidUntil": "2027-12-31",
            "description": "1 full audit, 2 scans per month, health score, listing optimizer, email alerts"
          },
          {
            "@type": "Offer",
            "name": "Starter",
            "price": "29",
            "priceCurrency": "USD",
            "priceValidUntil": "2027-12-31",
            "billingIncrement": "P1M",
            "description": "Weekly scans, app impact analysis, code residue detection, security monitoring, ghost billing detection"
          },
          {
            "@type": "Offer",
            "name": "Pro",
            "price": "79",
            "priceCurrency": "USD",
            "priceValidUntil": "2027-12-31",
            "billingIncrement": "P1M",
            "description": "Daily scans, real browser testing, visual diffs, AI readiness score, priority support"
          },
          {
            "@type": "Offer",
            "name": "Agency",
            "price": "199",
            "priceCurrency": "USD",
            "priceValidUntil": "2027-12-31",
            "billingIncrement": "P1M",
            "description": "Unlimited scans, multi-store support, dedicated account manager, custom integrations"
          }
        ],
        "publisher": {
          "@id": "https://storemd.vercel.app/#organization"
        }
      },
      {
        "@type": "FAQPage",
        "@id": "https://storemd.vercel.app/#faq",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "Which apps does StoreMD actually replace?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Most commonly: Booster SEO, SEO King, Smart SEO, Tapita, SearchPie, PageSpeed Optimizer, TinyIMG (SEO features), Accessibly, UserWay, accessiBe, Plug In SEO, broken link checkers, and LLMs.txt / AEO apps. If you have a specific app in mind, email us — we probably already replace it."
            }
          },
          {
            "@type": "Question",
            "name": "How is StoreMD different from the SEO/audit apps I already use?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Other apps read your metadata and send you a PDF. We actually use your store — real browser, real clicks, real checkout flow, real slow-network testing. And we don't stop at finding issues: we ship the fixes automatically. You wake up to results, not homework."
            }
          },
          {
            "@type": "Question",
            "name": "Do I really save $850/year switching?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Depends on your current stack. Run our free audit — we detect your installed apps and show you the exact number. Typical merchant: 5 apps at $150/month combined. StoreMD Pro: $79/month. That's $852/year saved. Plus your store runs faster because one script replaces five."
            }
          },
          {
            "@type": "Question",
            "name": "Will I lose my SEO data or settings if I switch?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "No. When you install Pro or Agency, we import configs from your previous apps — meta titles, alt text rules, redirects, schema. You start where you left off. Free migration included."
            }
          },
          {
            "@type": "Question",
            "name": "Is StoreMD really as good as a dedicated SEO app?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "For 95% of merchants, yes — we match or exceed core features. If you need deep keyword research or multi-country hreflang complexity, keep your specialist and use StoreMD for everything else (you'd still save 4 apps)."
            }
          },
          {
            "@type": "Question",
            "name": "Will StoreMD break my store?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "No. Every fix is reversible with one click. We log every change. Risky changes queue for your review — nothing touches your storefront without approval rules you control. We also never inject scripts; we only apply fixes via the Shopify API."
            }
          },
          {
            "@type": "Question",
            "name": "How long does a scan take?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "First scan: ~60 seconds. Scheduled scans run in the background and never interrupt traffic."
            }
          },
          {
            "@type": "Question",
            "name": "Will StoreMD slow down my store?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "The opposite. We don't inject scripts into your theme. We apply fixes via the Shopify API. Most stores get 0.8–1.5s faster within the first week after removing redundant audit apps."
            }
          },
          {
            "@type": "Question",
            "name": "What happens if I uninstall?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Subscription ends immediately. All changes are reversible in one click. Your data is deleted within 30 days."
            }
          },
          {
            "@type": "Question",
            "name": "Can I cancel anytime?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Yes. One click in Settings or through Shopify. No fees. No questions."
            }
          }
        ]
      }
    ]
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schemas) }}
    />
  );
}

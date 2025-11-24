"""CLI tool to ingest and extract knowledge from research papers.

Usage:
    python -m scripts.ingest_knowledge --articles-dir articles --output knowledge_base.json
"""
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.knowledge_extractor import (
    KnowledgeExtractor,
    save_knowledge_base,
    load_knowledge_base
)


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured knowledge from research papers and articles"
    )
    parser.add_argument(
        "--articles-dir",
        type=str,
        default="articles",
        help="Directory containing PDF files (default: articles)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/knowledge_base.json",
        help="Output JSON file for knowledge base (default: data/knowledge_base.json)"
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=5,
        help="Maximum chunks to process per document (default: 5)"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="data/knowledge_cache",
        help="Directory to cache individual document extractions (default: data/knowledge_cache)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching"
    )
    parser.add_argument(
        "--view",
        type=str,
        help="View existing knowledge base JSON file instead of processing"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # View mode
    if args.view:
        try:
            knowledge_list = load_knowledge_base(args.view)
            print(f"\n=== Knowledge Base: {args.view} ===")
            print(f"Total documents: {len(knowledge_list)}\n")
            
            for i, knowledge in enumerate(knowledge_list, 1):
                print(f"\n--- Document {i}: {knowledge.source} ---")
                if knowledge.title:
                    print(f"Title: {knowledge.title}")
                if knowledge.summary:
                    print(f"\nSummary:\n{knowledge.summary}")
                print(f"\nKey Concepts ({len(knowledge.key_concepts)}):")
                for concept in knowledge.key_concepts[:10]:
                    print(f"  • {concept}")
                if len(knowledge.key_concepts) > 10:
                    print(f"  ... and {len(knowledge.key_concepts) - 10} more")
                
                print(f"\nMain Findings ({len(knowledge.main_findings)}):")
                for finding in knowledge.main_findings[:5]:
                    print(f"  • {finding}")
                if len(knowledge.main_findings) > 5:
                    print(f"  ... and {len(knowledge.main_findings) - 5} more")
                
                print(f"\nData Points ({len(knowledge.data_points)}):")
                for data in knowledge.data_points[:5]:
                    print(f"  • {data}")
                if len(knowledge.data_points) > 5:
                    print(f"  ... and {len(knowledge.data_points) - 5} more")
                
                if knowledge.methodologies:
                    print(f"\nMethodologies ({len(knowledge.methodologies)}):")
                    for method in knowledge.methodologies[:3]:
                        print(f"  • {method}")
                
                if knowledge.citations:
                    print(f"\nCitations ({len(knowledge.citations)}):")
                    for citation in knowledge.citations[:5]:
                        print(f"  • {citation}")
            
            return
            
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            sys.exit(1)
    
    # Processing mode
    print(f"\n{'='*60}")
    print("Knowledge Ingestion System")
    print(f"{'='*60}\n")
    print(f"Articles directory: {args.articles_dir}")
    print(f"Output file: {args.output}")
    print(f"Max chunks per document: {args.max_chunks}")
    print(f"Cache directory: {args.cache_dir if not args.no_cache else 'disabled'}")
    print()
    
    # Check if articles directory exists
    if not Path(args.articles_dir).exists():
        print(f"Error: Directory '{args.articles_dir}' does not exist")
        sys.exit(1)
    
    # Initialize extractor
    print("Initializing LLM client...")
    try:
        extractor = KnowledgeExtractor()
        print(f"✓ Using provider: {extractor.llm.provider}, model: {extractor.llm.model}")
    except Exception as e:
        print(f"Error initializing LLM client: {e}")
        sys.exit(1)
    
    # Process documents
    print(f"\nProcessing PDFs from '{args.articles_dir}'...")
    print("(This may take several minutes depending on document size)\n")
    
    try:
        cache_dir = None if args.no_cache else args.cache_dir
        knowledge_list = extractor.process_directory(
            articles_dir=args.articles_dir,
            max_chunks_per_doc=args.max_chunks,
            cache_dir=cache_dir
        )
        
        if not knowledge_list:
            print("\nNo documents processed. Check if PDFs exist in the directory.")
            sys.exit(1)
        
        print(f"\n{'='*60}")
        print(f"Extraction Complete!")
        print(f"{'='*60}\n")
        print(f"Processed {len(knowledge_list)} documents")
        
        # Display summary
        for i, knowledge in enumerate(knowledge_list, 1):
            print(f"\n{i}. {knowledge.source}")
            if knowledge.title:
                print(f"   Title: {knowledge.title}")
            print(f"   - {len(knowledge.key_concepts)} key concepts")
            print(f"   - {len(knowledge.main_findings)} main findings")
            print(f"   - {len(knowledge.data_points)} data points")
            print(f"   - {len(knowledge.methodologies)} methodologies")
            print(f"   - {len(knowledge.citations)} citations")
        
        # Save knowledge base
        print(f"\nSaving knowledge base to '{args.output}'...")
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        save_knowledge_base(knowledge_list, args.output)
        
        print("\n✓ Knowledge base saved successfully!")
        print(f"\nTo view the results, run:")
        print(f"  python -m scripts.ingest_knowledge --view {args.output}")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Temporal Evolution Analysis for Voynich Manuscript

Analyzes token usage patterns across manuscript pages to detect:
- Token frequency evolution over time (page order)
- Vocabulary diversity changes across sections
- Temporal clustering of specific tokens
- Statistical shifts that might indicate authorial changes or topic shifts
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import entropy


class TemporalAnalyzer:
    """Analyzes temporal patterns in Voynich Manuscript token usage."""
    
    def __init__(self, token_coords_path: str, output_dir: str = "reports/figures/timeline"):
        """
        Initialize the temporal analyzer.
        
        Args:
            token_coords_path: Path to token_coords.jsonl file
            output_dir: Directory to save visualizations
        """
        self.token_coords_path = Path(token_coords_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.tokens_df = None
        self.folio_stats = None
        
    def load_data(self) -> pd.DataFrame:
        """Load token coordinate data."""
        print(f"Loading token data from {self.token_coords_path}...")
        
        tokens = []
        with open(self.token_coords_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    tokens.append(json.loads(line))
        
        self.tokens_df = pd.DataFrame(tokens)
        print(f"Loaded {len(self.tokens_df)} tokens from {self.tokens_df['folio'].nunique()} folios")
        
        return self.tokens_df
    
    def extract_folio_order(self, folio: str) -> Tuple[int, str]:
        """
        Extract numeric order and side from folio identifier.
        
        Args:
            folio: Folio identifier (e.g., "103v", "104r", "1r")
            
        Returns:
            Tuple of (numeric_page, side)
        """
        # Extract numeric part and side (r/v)
        import re
        match = re.match(r'(\d+)([rv])', folio)
        if match:
            num = int(match.group(1))
            side = match.group(2)
            # Recto (r) comes before verso (v)
            order = num * 2 + (0 if side == 'r' else 1)
            return order, side
        return 0, 'r'
    
    def compute_folio_statistics(self) -> pd.DataFrame:
        """Compute statistics for each folio."""
        if self.tokens_df is None:
            self.load_data()
        
        print("Computing folio-level statistics...")
        
        stats = []
        for folio in sorted(self.tokens_df['folio'].unique(), 
                          key=lambda x: self.extract_folio_order(x)[0]):
            folio_tokens = self.tokens_df[self.tokens_df['folio'] == folio]
            
            tokens_list = folio_tokens['token'].tolist()
            token_counts = Counter(tokens_list)
            
            order, side = self.extract_folio_order(folio)
            
            stat = {
                'folio': folio,
                'order': order,
                'side': side,
                'token_count': len(tokens_list),
                'unique_tokens': len(token_counts),
                'vocabulary_diversity': len(token_counts) / len(tokens_list) if tokens_list else 0,
                'most_common_token': token_counts.most_common(1)[0][0] if token_counts else None,
                'most_common_freq': token_counts.most_common(1)[0][1] if token_counts else 0,
                'repetition_rate': token_counts.most_common(1)[0][1] / len(tokens_list) if tokens_list else 0,
                'tokens': tokens_list
            }
            
            stats.append(stat)
        
        self.folio_stats = pd.DataFrame(stats)
        print(f"Computed statistics for {len(self.folio_stats)} folios")
        
        return self.folio_stats
    
    def analyze_token_evolution(self, token: str) -> Dict:
        """
        Analyze how a specific token's usage evolves across folios.
        
        Args:
            token: Token to analyze
            
        Returns:
            Dictionary with evolution statistics
        """
        if self.folio_stats is None:
            self.compute_folio_statistics()
        
        evolution = []
        for _, row in self.folio_stats.iterrows():
            token_freq = row['tokens'].count(token) / len(row['tokens']) if row['tokens'] else 0
            evolution.append({
                'folio': row['folio'],
                'order': row['order'],
                'frequency': token_freq,
                'absolute_count': row['tokens'].count(token)
            })
        
        evolution_df = pd.DataFrame(evolution)
        
        return {
            'token': token,
            'first_appearance': evolution_df[evolution_df['absolute_count'] > 0]['folio'].iloc[0] if any(evolution_df['absolute_count'] > 0) else None,
            'last_appearance': evolution_df[evolution_df['absolute_count'] > 0]['folio'].iloc[-1] if any(evolution_df['absolute_count'] > 0) else None,
            'total_occurrences': evolution_df['absolute_count'].sum(),
            'appears_in_folios': (evolution_df['absolute_count'] > 0).sum(),
            'evolution': evolution_df
        }
    
    def detect_vocabulary_shifts(self, window_size: int = 2) -> pd.DataFrame:
        """
        Detect significant vocabulary shifts across manuscript sections.
        
        Args:
            window_size: Number of folios to include in rolling window
            
        Returns:
            DataFrame with vocabulary shift metrics
        """
        if self.folio_stats is None:
            self.compute_folio_statistics()
        
        print(f"Detecting vocabulary shifts with window size {window_size}...")
        
        shifts = []
        
        for i in range(len(self.folio_stats) - window_size):
            window1 = self.folio_stats.iloc[i:i+window_size]
            window2 = self.folio_stats.iloc[i+window_size:i+2*window_size]
            
            # Collect all tokens from each window
            tokens1 = []
            tokens2 = []
            for tokens in window1['tokens']:
                tokens1.extend(tokens)
            for tokens in window2['tokens']:
                tokens2.extend(tokens)
            
            if not tokens1 or not tokens2:
                continue
            
            # Calculate vocabulary overlap
            vocab1 = set(tokens1)
            vocab2 = set(tokens2)
            
            overlap = len(vocab1 & vocab2)
            union = len(vocab1 | vocab2)
            jaccard = overlap / union if union > 0 else 0
            
            # Calculate frequency distribution similarity (JSD)
            counter1 = Counter(tokens1)
            counter2 = Counter(tokens2)
            
            all_tokens = set(counter1.keys()) | set(counter2.keys())
            
            freq1 = np.array([counter1.get(t, 0) for t in all_tokens])
            freq2 = np.array([counter2.get(t, 0) for t in all_tokens])
            
            freq1 = freq1 / freq1.sum()
            freq2 = freq2 / freq2.sum()
            
            # Jensen-Shannon Divergence
            m = 0.5 * (freq1 + freq2)
            jsd = 0.5 * entropy(freq1, m) + 0.5 * entropy(freq2, m)
            
            shifts.append({
                'window_start': window1['folio'].iloc[0],
                'window_end': window2['folio'].iloc[-1],
                'jaccard_similarity': jaccard,
                'jsd_distance': jsd,
                'vocab_size_1': len(vocab1),
                'vocab_size_2': len(vocab2),
                'new_tokens': len(vocab2 - vocab1),
                'disappeared_tokens': len(vocab1 - vocab2)
            })
        
        shifts_df = pd.DataFrame(shifts)
        print(f"Detected {len(shifts_df)} vocabulary shift measurements")
        
        return shifts_df
    
    def visualize_token_frequency_evolution(self, top_n: int = 10):
        """
        Create visualization of top N tokens' frequency evolution.
        
        Args:
            top_n: Number of most frequent tokens to visualize
        """
        if self.folio_stats is None:
            self.compute_folio_statistics()
        
        print(f"Visualizing evolution of top {top_n} tokens...")
        
        # Get overall most common tokens
        all_tokens = []
        for tokens in self.folio_stats['tokens']:
            all_tokens.extend(tokens)
        
        top_tokens = [token for token, _ in Counter(all_tokens).most_common(top_n)]
        
        # Build frequency matrix
        freq_matrix = []
        for token in top_tokens:
            evolution = self.analyze_token_evolution(token)
            freq_matrix.append(evolution['evolution']['frequency'].values)
        
        freq_df = pd.DataFrame(
            freq_matrix,
            index=top_tokens,
            columns=self.folio_stats['folio'].values
        )
        
        # Create heatmap
        plt.figure(figsize=(14, 8))
        sns.heatmap(freq_df, cmap='YlOrRd', annot=True, fmt='.2f', 
                   cbar_kws={'label': 'Token Frequency'})
        plt.title(f'Token Frequency Evolution Across Manuscript (Top {top_n} Tokens)', 
                 fontsize=14, fontweight='bold')
        plt.xlabel('Folio', fontsize=12)
        plt.ylabel('Token', fontsize=12)
        plt.tight_layout()
        
        output_path = self.output_dir / 'token_frequency_heatmap.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved heatmap to {output_path}")
        plt.close()
    
    def visualize_vocabulary_diversity(self):
        """Create visualization of vocabulary diversity over time."""
        if self.folio_stats is None:
            self.compute_folio_statistics()
        
        print("Visualizing vocabulary diversity evolution...")
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Vocabulary diversity (type-token ratio)
        axes[0].plot(range(len(self.folio_stats)), 
                    self.folio_stats['vocabulary_diversity'], 
                    marker='o', linewidth=2, markersize=6, color='steelblue')
        axes[0].axhline(self.folio_stats['vocabulary_diversity'].mean(), 
                       color='red', linestyle='--', linewidth=2, 
                       label=f'Mean: {self.folio_stats["vocabulary_diversity"].mean():.3f}')
        axes[0].set_xlabel('Folio Sequence', fontsize=12)
        axes[0].set_ylabel('Vocabulary Diversity\n(Type-Token Ratio)', fontsize=12)
        axes[0].set_title('Vocabulary Diversity Evolution Across Manuscript', 
                         fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        axes[0].set_xticks(range(len(self.folio_stats)))
        axes[0].set_xticklabels(self.folio_stats['folio'], rotation=45, ha='right')
        
        # Plot 2: Token count and unique tokens
        x = range(len(self.folio_stats))
        axes[1].bar(x, self.folio_stats['token_count'], alpha=0.6, 
                   label='Total Tokens', color='skyblue')
        axes[1].plot(x, self.folio_stats['unique_tokens'], marker='o', 
                    linewidth=2, markersize=6, color='darkgreen', 
                    label='Unique Tokens')
        axes[1].set_xlabel('Folio Sequence', fontsize=12)
        axes[1].set_ylabel('Count', fontsize=12)
        axes[1].set_title('Token Count vs Unique Tokens per Folio', 
                         fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3, axis='y')
        axes[1].legend()
        axes[1].set_xticks(range(len(self.folio_stats)))
        axes[1].set_xticklabels(self.folio_stats['folio'], rotation=45, ha='right')
        
        plt.tight_layout()
        
        output_path = self.output_dir / 'vocabulary_diversity_evolution.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved diversity plot to {output_path}")
        plt.close()
    
    def visualize_vocabulary_shifts(self):
        """Visualize vocabulary shifts between manuscript sections."""
        shifts = self.detect_vocabulary_shifts(window_size=1)
        
        if shifts.empty:
            print("No vocabulary shifts detected")
            return
        
        print("Visualizing vocabulary shifts...")
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Jaccard similarity
        x = range(len(shifts))
        axes[0].plot(x, shifts['jaccard_similarity'], marker='o', 
                    linewidth=2, markersize=6, color='purple')
        axes[0].axhline(shifts['jaccard_similarity'].mean(), 
                       color='red', linestyle='--', linewidth=2,
                       label=f'Mean: {shifts["jaccard_similarity"].mean():.3f}')
        axes[0].set_xlabel('Window Transition', fontsize=12)
        axes[0].set_ylabel('Jaccard Similarity', fontsize=12)
        axes[0].set_title('Vocabulary Overlap Between Adjacent Folio Windows', 
                         fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        axes[0].set_ylim(0, 1)
        
        # Plot 2: Jensen-Shannon Divergence
        axes[1].plot(x, shifts['jsd_distance'], marker='s', 
                    linewidth=2, markersize=6, color='coral')
        axes[1].axhline(shifts['jsd_distance'].mean(), 
                       color='red', linestyle='--', linewidth=2,
                       label=f'Mean: {shifts["jsd_distance"].mean():.3f}')
        axes[1].set_xlabel('Window Transition', fontsize=12)
        axes[1].set_ylabel('Jensen-Shannon Divergence', fontsize=12)
        axes[1].set_title('Statistical Distance Between Adjacent Folio Windows', 
                         fontsize=14, fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        
        plt.tight_layout()
        
        output_path = self.output_dir / 'vocabulary_shifts.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Saved vocabulary shifts plot to {output_path}")
        plt.close()
    
    def generate_timeline_report(self) -> str:
        """
        Generate comprehensive timeline analysis report.
        
        Returns:
            Markdown-formatted report text
        """
        if self.folio_stats is None:
            self.compute_folio_statistics()
        
        print("Generating timeline analysis report...")
        
        # Compute overall statistics
        all_tokens = []
        for tokens in self.folio_stats['tokens']:
            all_tokens.extend(tokens)
        
        token_counter = Counter(all_tokens)
        top_5_tokens = token_counter.most_common(5)
        
        shifts = self.detect_vocabulary_shifts(window_size=1)
        
        # Find most significant shift
        if not shifts.empty:
            max_shift_idx = shifts['jsd_distance'].idxmax()
            max_shift = shifts.iloc[max_shift_idx]
        else:
            max_shift = None
        
        report = f"""# Timeline Analysis Report

## Overview

This report analyzes the temporal evolution of token usage across the Voynich Manuscript, 
examining how vocabulary, token frequency, and writing patterns change across folios.

**Analysis Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## Dataset Summary

- **Total Folios Analyzed**: {len(self.folio_stats)}
- **Total Tokens**: {len(all_tokens)}
- **Unique Tokens**: {len(token_counter)}
- **Global Vocabulary Diversity**: {len(token_counter) / len(all_tokens):.3f}

### Folio Coverage

{self.folio_stats[['folio', 'token_count', 'unique_tokens', 'vocabulary_diversity']].to_markdown(index=False)}

## Top Tokens Across Manuscript

The most frequent tokens throughout the entire manuscript:

"""
        for i, (token, count) in enumerate(top_5_tokens, 1):
            freq = count / len(all_tokens) * 100
            report += f"{i}. **{token}**: {count} occurrences ({freq:.2f}%)\n"
        
        report += f"""

## Vocabulary Diversity Evolution

Vocabulary diversity (type-token ratio) measures how varied the language is in each folio.
Higher values indicate more varied vocabulary, while lower values suggest repetitive text.

- **Mean Diversity**: {self.folio_stats['vocabulary_diversity'].mean():.3f}
- **Std Deviation**: {self.folio_stats['vocabulary_diversity'].std():.3f}
- **Min Diversity**: {self.folio_stats['vocabulary_diversity'].min():.3f} (Folio: {self.folio_stats.loc[self.folio_stats['vocabulary_diversity'].idxmin(), 'folio']})
- **Max Diversity**: {self.folio_stats['vocabulary_diversity'].max():.3f} (Folio: {self.folio_stats.loc[self.folio_stats['vocabulary_diversity'].idxmax(), 'folio']})

"""
        
        if max_shift is not None:
            report += f"""## Vocabulary Shifts

Analysis of vocabulary changes between adjacent folio windows reveals areas where 
the manuscript's language shifts significantly.

### Most Significant Shift

The largest vocabulary shift occurs between **{max_shift['window_start']}** and **{max_shift['window_end']}**:

- **Jensen-Shannon Divergence**: {max_shift['jsd_distance']:.3f}
- **Jaccard Similarity**: {max_shift['jaccard_similarity']:.3f}
- **New Tokens Introduced**: {max_shift['new_tokens']}
- **Tokens Disappeared**: {max_shift['disappeared_tokens']}

This shift might indicate:
- Change in topic or subject matter
- Different scribe or author
- Transition between manuscript sections
- Different encoding or cipher system

### Shift Summary Statistics

- **Mean Jaccard Similarity**: {shifts['jaccard_similarity'].mean():.3f}
- **Mean JS Divergence**: {shifts['jsd_distance'].mean():.3f}
- **Vocabulary Stability**: {"High" if shifts['jaccard_similarity'].mean() > 0.7 else "Moderate" if shifts['jaccard_similarity'].mean() > 0.5 else "Low"}

"""
        
        # Analyze specific token patterns
        report += f"""## Token-Specific Evolution

### Most Common Token Analysis: "{top_5_tokens[0][0]}"

"""
        
        top_token_evolution = self.analyze_token_evolution(top_5_tokens[0][0])
        
        report += f"""- **First Appearance**: {top_token_evolution['first_appearance']}
- **Last Appearance**: {top_token_evolution['last_appearance']}
- **Total Occurrences**: {top_token_evolution['total_occurrences']}
- **Appears in {top_token_evolution['appears_in_folios']} / {len(self.folio_stats)} folios** ({top_token_evolution['appears_in_folios'] / len(self.folio_stats) * 100:.1f}%)

## Key Findings

1. **Vocabulary Consistency**: The manuscript shows {'relatively stable' if self.folio_stats['vocabulary_diversity'].std() < 0.1 else 'significant variation in'} vocabulary diversity across folios (σ = {self.folio_stats['vocabulary_diversity'].std():.3f}).

2. **Token Distribution**: The top 5 tokens account for {sum(c for _, c in top_5_tokens) / len(all_tokens) * 100:.1f}% of all tokens, suggesting {'high repetitiveness' if sum(c for _, c in top_5_tokens) / len(all_tokens) > 0.3 else 'moderate linguistic diversity'}.

3. **Temporal Patterns**: {'Significant vocabulary shifts detected' if max_shift is not None and max_shift['jsd_distance'] > 0.3 else 'Vocabulary remains relatively stable'} across the manuscript's folios.

4. **Scribe Consistency**: The {'low' if self.folio_stats['vocabulary_diversity'].std() < 0.1 else 'moderate to high'} variation in vocabulary diversity {'supports' if self.folio_stats['vocabulary_diversity'].std() < 0.1 else 'may challenge'} the hypothesis of a single scribe.

## Implications for Decipherment

The temporal analysis reveals:

- **Encoding Consistency**: {'The manuscript appears to use consistent encoding throughout' if not shifts.empty and shifts['jsd_distance'].mean() < 0.3 else 'Significant statistical shifts suggest possible multiple encoding schemes or topic changes'}
- **Linguistic Structure**: {'Strong repetition patterns consistent with constructed language or cipher' if sum(c for _, c in top_5_tokens) / len(all_tokens) > 0.3 else 'Vocabulary distribution more typical of natural language'}
- **Manuscript Sections**: {'Clear vocabulary boundaries suggest distinct sections or topics' if max_shift is not None and max_shift['jsd_distance'] > 0.5 else 'Smooth vocabulary transitions suggest unified composition'}

## Visualizations Generated

1. `token_frequency_heatmap.png` - Evolution of top token frequencies across folios
2. `vocabulary_diversity_evolution.png` - Vocabulary diversity and token counts over time
3. `vocabulary_shifts.png` - Statistical similarity between adjacent folio windows

## Recommendations for Further Analysis

1. **Contextual Analysis**: Correlate vocabulary shifts with manuscript illustrations and diagrams
2. **Expanded Corpus**: Apply analysis to full manuscript transcription (currently limited to sample)
3. **Cross-Reference**: Compare temporal patterns with known historical manuscript conventions
4. **Statistical Modeling**: Build predictive models for token sequences based on temporal position

---

*Generated by Voynich Decoder Timeline Analytics*
"""
        
        return report
    
    def run_full_analysis(self):
        """Run complete timeline analysis pipeline."""
        print("=" * 60)
        print("VOYNICH MANUSCRIPT TIMELINE ANALYSIS")
        print("=" * 60)
        print()
        
        # Load data
        self.load_data()
        
        # Compute statistics
        self.compute_folio_statistics()
        
        # Generate visualizations
        self.visualize_token_frequency_evolution(top_n=10)
        self.visualize_vocabulary_diversity()
        self.visualize_vocabulary_shifts()
        
        # Generate report
        report = self.generate_timeline_report()
        
        # Save report
        report_path = self.output_dir.parent / 'timeline_analysis.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print()
        print(f"Timeline analysis complete! Report saved to {report_path}")
        print(f"Visualizations saved to {self.output_dir}")
        
        return report


def main():
    """Main entry point for timeline analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze temporal patterns in Voynich Manuscript')
    parser.add_argument('--token-coords', type=str, 
                       default='data/processed/token_coords.jsonl',
                       help='Path to token coordinates file')
    parser.add_argument('--output-dir', type=str,
                       default='reports/figures/timeline',
                       help='Directory for output visualizations')
    
    args = parser.parse_args()
    
    analyzer = TemporalAnalyzer(args.token_coords, args.output_dir)
    analyzer.run_full_analysis()


if __name__ == '__main__':
    main()

'use client'

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import SearchBar from '@/components/search-bar';
import { Button } from '@/components/ui/button';

// Helper for icons
const Icon = ({ path, className = "h-4 w-4" }: { path: string; className?: string }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className={className}
  >
    <path d={path} />
  </svg>
);

// Mock data for status widgets
const statusWidgets = [
  {
    title: '총 법령 수',
    value: '21,849',
    icon: 'M14.5,9H13V3H11v6H9.5L12,11.5L14.5,9z M18,15H6v-4h12V15z M12,13c-0.55,0-1-0.45-1-1s0.45-1,1-1s1,0.45,1,1S12.55,13,12,13z M19,21H5a2,2,0,0,1-2-2V5a2,2,0,0,1,2-2h14a2,2,0,0,1,2,2v14A2,2,0,0,1,19,21z',
  },
  {
    title: '총 판례 수',
    value: '3,412,551',
    icon: 'M19,3H5A2,2,0,0,0,3,5V19a2,2,0,0,0,2,2H19a2,2,0,0,0,2-2V5A2,2,0,0,0,19,3z M10,17H7v-2h3V17z M17,12H7V10h10V12z M17,7H7V5h10V7z',
  },
  {
    title: '마지막 업데이트',
    value: '오늘 08:00',
    icon: 'M11.99,2C6.47,2,2,6.48,2,12s4.47,10,9.99,10C17.52,22,22,17.52,22,12S17.52,2,11.99,2z M12,20c-4.42,0-8-3.58-8-8s3.58-8,8-8s8,3.58,8,8S16.42,20,12,20z M12.5,7H11v6l5.25,3.15L17,14.92,12.5,12V7z',
  },
];

export default function MainPage() {
  const [query, setQuery] = useState('');
  const router = useRouter();

  const handleSearchSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (query.trim()) {
      // Redirect to chat page with the query
      router.push(`/chat?query=${encodeURIComponent(query)}`);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section with Search */}
      <div className="text-center py-16 px-4">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          법률 AI 어시스턴트
        </h1>
        <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
          21,849개 법령과 3,412,551개 판례를 기반으로 한 전문적인 법률 상담을 받아보세요
        </p>

        {/* Search Bar */}
        <div className="mb-16">
          <SearchBar
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onSubmit={handleSearchSubmit}
          />
        </div>
      </div>

      {/* Status Widgets */}
      <div className="max-w-7xl mx-auto px-4 mb-16">
        <div className="grid gap-6 md:grid-cols-3">
          {statusWidgets.map((widget, index) => (
            <Card key={index} className="group">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {widget.title}
                </CardTitle>
                <Icon path={widget.icon} className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{widget.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Daily Briefing Card */}
      <div className="max-w-4xl mx-auto px-4">
        <Card className="group">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span>오늘의 법률 브리핑</span>
              <div className="h-2 w-2 bg-green-500 rounded-full"></div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <h3 className="font-semibold text-lg mb-2">주요 변경 사항</h3>
              <p className="text-muted-foreground leading-relaxed">
                오늘 개정된 법령: <Link href="/chat?query=자본시장법" className="text-primary hover:underline font-medium">자본시장법</Link>, <Link href="/chat?query=개인정보보호법 제23조" className="text-primary hover:underline font-medium">개인정보보호법 제23조</Link> (민감정보의 처리 제한) 신설. 신규 판례 12건 추가. 총 5개의 법령수정이 이뤄졌습니다.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-lg mb-2">최신 동향 분석</h3>
              <p className="text-muted-foreground leading-relaxed">
                전반적으로 금융소비자 보호 및 내부통제 관련 규제 강화 기조가 이어지는 중입니다. 특히 ELS 등 고위험 금융상품 판매 관련 규제가 구체화되고 있습니다.
              </p>
            </div>
            <div className="flex justify-end pt-4">
               <Button variant="outline" asChild className="hover:bg-primary hover:text-primary-foreground">
                  <Link href="/chat">브리핑 전체 내용 보기</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}